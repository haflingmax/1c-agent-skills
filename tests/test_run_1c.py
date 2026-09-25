"""Обёртка запуска 1cv8: проверяет, дожидается, ставит диагноз.

Настоящий 1cv8 в тестах не запускается — вместо него подставной `.cmd`,
умеющий ровно то, что надо проверить. Приём уже применён в наборе:
tools/prove-blocking-rules.ps1 и свидетельство
docs/evidence/2026-08-22-blocking-rules.md.

Подставной файл именно `.cmd`, а не скрипт на Python: так обёртка запускает
его тем же способом, что и настоящую программу, и в рабочем коде
не заводится параметр, нужный одним лишь тестам.

Запуск: python -m pytest tests/test_run_1c.py -v
"""
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "1c-build-and-db" / "scripts" / "run-1c.py"

spec = importlib.util.spec_from_file_location("run_1c", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["run_1c"] = mod
spec.loader.exec_module(mod)


def база(где, размер=10):
    б = где / "base"
    б.mkdir(parents=True)
    (б / "1Cv8.1CD").write_bytes(b"x" * размер)
    return б


ЗАГЛУШКИ = {
    # что проверяем: (тело для cmd.exe, тело для POSIX-оболочки)
    "молчит и не завершается": ("ping -n 31 127.0.0.1 >nul\r\n", "sleep 30\n"),
    "сразу выходит": ("exit /b 0\r\n", "exit 0\n"),
    "печатает третий аргумент": ("echo %3\r\n", 'echo "$3"\n'),
}


def заглушка(tmp_path, что, имя="подставной-1cv8"):
    """Подставная «платформа»: делает ровно то, что нужно проверить.

    Тело выбирается по ОС: `.cmd` в Windows, исполняемый скрипт с шебангом
    на POSIX. Без этого тесты обёртки были привязаны к Windows, а прибор
    набора обязан быть надёжен в любой среде — правило принято 25.09.2026.
    """
    для_cmd, для_posix = ЗАГЛУШКИ[что]
    if os.name == "nt":
        ф = tmp_path / (имя + ".cmd")
        ф.write_text("@echo off\r\n" + для_cmd, encoding="ascii", newline="")
        return ф
    ф = tmp_path / (имя + ".sh")
    ф.write_text("#!/bin/sh\n" + для_posix, encoding="ascii", newline="")
    ф.chmod(0o755)
    return ф


def test_refuses_to_run_a_command_that_fails_the_check():
    """Непрошедшая проверку команда не запускается вовсе.

    Команда инцидента 28.08.2026: CONFIG — не режим запуска. Проверяльщик
    отказал бы на первой же попытке, но его не вызывали.
    """
    код, отчёт = mod.запустить("1cv8 CONFIG /F d:/нет /LoadCfg a.cf",
                               ответы=set(), таймаут=5)
    assert код == 2
    assert "K002" in отчёт, "в отчёте обязан быть код отказа проверяльщика"
    assert "запуск не выполнялся" in отчёт


def test_hang_with_untouched_base_is_diagnosed(tmp_path):
    """Процесс жив, вывод пуст, файл базы не менялся — это модальный диалог.

    Инцидент 28.08.2026: три запуска подряд «висели» с пустым выводом,
    и агент принял это за особенность своей среды. На деле платформа ждала
    ответа в диалоге авторизации, невидимом для скрытого процесса.
    """
    б = база(tmp_path)
    тихий = заглушка(tmp_path, "молчит и не завершается")
    команда = ('%s DESIGNER /F "%s" /N Admin /P"" /LoadCfg a.cf '
               '/UpdateDBCfg -Dynamic- /DisableStartupDialogs /Out log.txt'
               % (тихий, б))
    код, отчёт = mod.запустить(команда, ответы={"база-одноразовая"}, таймаут=3)
    assert код == 3
    assert "модальный диалог" in отчёт


def test_unchanged_base_after_success_is_named(tmp_path):
    """Код 0 при неизменившемся файле базы — повод сказать, а не радоваться.

    Постмортем: «если 1Cv8.1CD LastWriteTime не изменился после операции —
    операция не прошла. Не искать причину в логах, проверить вход».
    """
    б = база(tmp_path)
    пустышка = заглушка(tmp_path, "сразу выходит")
    команда = ('%s DESIGNER /F "%s" /N Admin /P"" /LoadCfg a.cf '
               '/UpdateDBCfg -Dynamic- /DisableStartupDialogs /Out log.txt'
               % (пустышка, б))
    код, отчёт = mod.запустить(команда, ответы={"база-одноразовая"}, таймаут=30)
    assert код == 0
    assert "не изменился" in отчёт


def test_quoted_path_with_spaces_reaches_the_program(tmp_path):
    """Кавычки вокруг пути снимаются: программа получает путь, а не кавычки.

    Без этого путь с пробелом уезжает в процесс вместе с кавычками, и
    платформа ищет базу по имени, которого нет. Тот же класс, что потеря
    кавычек в PowerShell (tools/native-arg.ps1).
    """
    б = база(tmp_path / "1C bases")
    эхо = заглушка(tmp_path, "печатает третий аргумент")
    команда = ('%s DESIGNER /F "%s" /N Admin /P"" /LoadCfg a.cf '
               '/UpdateDBCfg -Dynamic- /DisableStartupDialogs /Out log.txt'
               % (эхо, б))
    код, отчёт = mod.запустить(команда, ответы={"база-одноразовая"}, таймаут=30)
    assert код == 0
    # Кавычки вокруг echo добавляет сам cmd.exe, когда аргумент содержит
    # пробел, — это его поведение, а не наше. Проверяем то, что наше:
    # путь доехал целиком, а не разорвался по пробелу на два аргумента.
    пришло = отчёт.splitlines()[-1].strip().strip('"')
    assert пришло == str(б), отчёт


def test_hang_is_reported_early_not_only_at_timeout(tmp_path, capsys):
    """Диагноз печатается, пока обёртку ещё не убили.

    Инструмент bash у агента убивает процесс по своему таймауту — обычно
    задолго до часа, который стоит у обёртки по умолчанию. Отчёт печатался
    только в конце, значит при зависании агент не видел ничего: ни диагноза,
    ни причины. Третья из трёх заявленных ценностей обёртки была
    недостижима. Взято в работу 24.09.2026 из отложенных.
    """
    б = база(tmp_path)
    тихий = заглушка(tmp_path, "молчит и не завершается")
    команда = ('%s DESIGNER /F "%s" /N Admin /P"" /LoadCfg a.cf '
               '/UpdateDBCfg -Dynamic- /DisableStartupDialogs /Out log.txt'
               % (тихий, б))
    mod.запустить(команда, ответы={"база-одноразовая"}, таймаут=6,
                  порог_подозрения=2)
    напечатано = capsys.readouterr().out
    assert "модальный диалог" in напечатано, (
        "диагноз не напечатан до конца ожидания: %r" % напечатано)


# --- Форма со списком аргументов (25.09.2026) ---
# Живой прогон: модель передала команду одной строкой из PowerShell, тот съел
# внутренние кавычки, и argparse увидел десяток позиционных аргументов вместо
# одного. Дважды получив usage, модель написала свой запускатель. Причина —
# не в кавычках, а в интерфейсе: строку с кавычками внутри ни одна оболочка
# не сохраняет одинаково, а ОТДЕЛЬНЫЙ аргумент умеет закавычить каждая.


def test_command_as_argument_list_after_dash_dash(tmp_path):
    """Команда после `--` принимается списком: разбора строки нет вовсе."""
    б = база(tmp_path)
    пустышка = заглушка(tmp_path, "сразу выходит")
    код = mod.main(["--ответ", "база-одноразовая", "--",
                    str(пустышка), "DESIGNER", "/F", str(б), "/N", "Admin",
                    "/P", "", "/LoadCfg", "a.cf", "/UpdateDBCfg", "-Dynamic-",
                    "/DisableStartupDialogs", "/Out", "log.txt"])
    assert код == 0


def test_argument_list_survives_a_space_in_the_program_path(tmp_path):
    r"""Пробел в пути к программе больше не ломает вызов.

    Это ровно то, на чём встал живой прогон: «C:\Program Files\...» после
    съеденных кавычек разорвалось на два аргумента. В форме со списком
    оболочка закавычивает каждый аргумент отдельно, и это умеют все.
    """
    каталог = tmp_path / "Program Files"
    каталог.mkdir()
    б = база(tmp_path)
    пустышка = заглушка(каталог, "сразу выходит")
    код = mod.main(["--ответ", "база-одноразовая", "--",
                    str(пустышка), "DESIGNER", "/F", str(б), "/N", "Admin",
                    "/P", "", "/DumpCfg", "out.cf",
                    "/DisableStartupDialogs", "/Out", "log.txt"])
    assert код == 0


def test_string_form_still_works(tmp_path):
    """Старая форма одной строкой не сломана: на неё опираются примеры."""
    б = база(tmp_path)
    пустышка = заглушка(tmp_path, "сразу выходит")
    команда = ('%s DESIGNER /F "%s" /N Admin /P"" /DumpCfg out.cf '
               '/DisableStartupDialogs /Out log.txt' % (пустышка, б))
    код, _ = mod.запустить(команда, ответы={"база-одноразовая"}, таймаут=30)
    assert код == 0


# --- Кавычки внутри элемента списка (25.09.2026, второй живой прогон) ---


def test_quotes_inside_a_list_element_are_removed():
    """Кавычки внутри аргумента убираются: иначе платформа получает мусор.

    Popen на Windows собирает строку через list2cmdline, а тот экранирует
    кавычку внутри аргумента как \\". Платформа видит /F\\"D:/база\\"
    и падает на пути. Проверено запуском 25.09.2026: с кавычками —
    «Неправильный путь к файлу», без них — «Сохранение конфигурации
    успешно завершено».

    В форме со списком кавычки не нужны вовсе: границу значения задаёт
    сам аргумент, а путь Windows кавычку содержать не может.
    """
    дано = ['1cv8.exe', 'DESIGNER', '/F"D:/1C/base/trade"', '/DumpCfg', 'a.cf']
    стало = mod._подготовить_аргументы(дано)
    assert стало == ['1cv8.exe', 'DESIGNER', '/FD:/1C/base/trade', '/DumpCfg', 'a.cf']


def test_empty_quoted_value_becomes_an_empty_argument():
    """/P"" — это ключ и ПУСТОЕ значение, а не ключ с кавычками.

    Проверено запуском: /P с отдельным пустым аргументом даёт код 0
    и успешную выгрузку, а слитное /P"" — «Пользователь ИБ не
    идентифицирован». Просто убрать кавычки нельзя: пустой пароль
    потерялся бы, и платформа приняла бы за него следующий ключ.
    """
    стало = mod._подготовить_аргументы(['1cv8.exe', 'DESIGNER', '/P""', '/DumpCfg'])
    assert стало == ['1cv8.exe', 'DESIGNER', '/P', '', '/DumpCfg']


def test_path_with_space_survives_as_its_own_element():
    """Путь с пробелом отдельным элементом не трогаем: он уже целый."""
    дано = ['1cv8.exe', '/F', 'D:/1C base/trade', '/DumpCfg', 'a.cf']
    assert mod._подготовить_аргументы(дано) == дано


# --- Пустой пароль без пустого аргумента (25.09.2026, третий живой прогон) ---
# PowerShell 5.1 молча выбрасывает пустой аргумент при вызове нативной
# программы: «/P ""» доезжает как голый «/P», и платформа берёт за пароль
# следующий ключ. Проверено печатью sys.argv и запуском на живой базе.
# Значит форма, которой учила ПОДСКАЗКА, в этой оболочке невыразима вовсе,
# и нужна такая, где пустого аргумента нет ни на одном участке пути.


def test_empty_password_flag_adds_the_pair_itself(tmp_path):
    """--пустой-пароль дорисовывает /P и пустую строку уже внутри Python."""
    б = база(tmp_path)
    пустышка = заглушка(tmp_path, "сразу выходит")
    код = mod.main(["--ответ", "база-одноразовая", "--пустой-пароль", "--",
                    str(пустышка), "DESIGNER", "/F", str(б), "/N", "Admin",
                    "/DumpCfg", "out.cf", "/DisableStartupDialogs",
                    "/Out", "log.txt"])
    assert код == 0


def test_empty_password_flag_survives_a_shell_that_drops_empty_arguments():
    """Флаг без значения не может быть съеден: съедать нечего."""
    аргументы = mod._дописать_пустой_пароль(
        ["1cv8.exe", "DESIGNER", "/F", "d:/base", "/N", "Админ",
         "/DisableStartupDialogs"])
    assert аргументы[-2:] == ["/P", ""]


def test_empty_password_flag_is_not_added_twice():
    """Если /P уже задан, второй паре взяться неоткуда."""
    дано = ["1cv8.exe", "DESIGNER", "/F", "d:/base", "/N", "Админ", "/P", "тайна"]
    assert mod._дописать_пустой_пароль(дано) == дано


def test_hint_teaches_the_flag_not_the_broken_pair():
    """ПОДСКАЗКА больше не учит форме, невыразимой в PowerShell 5.1."""
    assert "--пустой-пароль" in mod.ПОДСКАЗКА
    assert '/P ""' not in mod.ПОДСКАЗКА


# --- Замер через настоящую оболочку ---
# Все тесты выше зовут main([...]) списком Python, и оболочки в популяции
# замера нет. Именно поэтому потеря пустого аргумента прошла мимо 600
# зелёных тестов. Здесь команда идёт тем же путём, что у агента:
# PowerShell 5.1 → python → обёртка.

import shutil
import subprocess as _sp

import pytest

_PS = shutil.which("powershell")


def _через_powershell(tmp_path, хвост):
    """Команда пишется в .ps1 и запускается через -File.

    Не через -Command: тогда строка команды сама проходит разбор
    командной строки powershell.exe, и кавычки переделываются ещё
    до того, как их увидит интерпретатор. Первая редакция теста шла
    через -Command и проверяла не то место — пустая пара доезжала
    непустой. Файл пишется с BOM: без него PowerShell 5.1 читает
    кириллицу в .ps1 как ANSI и падает в чужом месте.
    """
    б = база(tmp_path)
    # Имя «1cv8», а не «подставной-1cv8»: проверяльщик опознаёт платформу
    # по имени файла, и под чужим именем отвечает K017 «вне компетенции»,
    # не проверяя ничего. Первый прогон теста на этом и прошёл мимо.
    пустышка = заглушка(tmp_path, "сразу выходит", имя="1cv8")
    сценарий = tmp_path / "zapusk.ps1"
    сценарий.write_text(
        "& '%s' '%s' --ответ база-одноразовая %s -- '%s' DESIGNER /F '%s' "
        "/N Admin %s /DumpCfg out.cf /DisableStartupDialogs /Out log.txt\r\n"
        "exit $LASTEXITCODE\r\n"
        % (sys.executable, SCRIPT, хвост[0], пустышка, б, хвост[1]),
        encoding="utf-8-sig")
    return _sp.run([_PS, "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(сценарий)],
                   capture_output=True, timeout=120,
                   env=dict(os.environ, PYTHONIOENCODING="utf-8"))


@pytest.mark.skipif(_PS is None, reason="нет Windows PowerShell")
def test_empty_pair_through_powershell_is_refused_not_launched(tmp_path):
    """/P "" через PowerShell 5.1 теряет пустую строку — обёртка обязана
    отказать кодом 2, а не запустить платформу с чужим ключом в пароле."""
    р = _через_powershell(tmp_path, ("", '/P ""'))
    вывод = р.stdout.decode("utf-8", errors="replace")
    assert р.returncode == 2, вывод
    assert "K022" in вывод, вывод


@pytest.mark.skipif(_PS is None, reason="нет Windows PowerShell")
def test_empty_password_flag_through_powershell_launches(tmp_path):
    """Флаг --пустой-пароль переживает PowerShell 5.1: запуск состоялся."""
    р = _через_powershell(tmp_path, ("--пустой-пароль", ""))
    вывод = р.stdout.decode("utf-8", errors="replace")
    assert р.returncode == 0, вывод
    assert "K022" not in вывод, вывод


# --- Работа против ожидания (25.09.2026, четвёртый живой прогон) ---
# Прежний признак зависания — «вывод пуст, 1Cv8.1CD не менялся» — ложен
# для любой долгой пакетной операции: /Out пишется в конце, а время правки
# файла базы, открытого на запись, на Windows не обновляется до закрытия.
# Проверено запуском: /DumpConfigToFiles шёл, 74 с процессорного времени
# и 4000 выгруженных файлов, а обёртка дважды напечатала «модальный диалог…
# Не ждать дольше». В Codex агент по этой подсказке убил загрузку
# конфигурации на третьей минуте. Различает работу и ожидание не файл,
# а процессорное время процесса.


def _крутит_процессор(секунд):
    """Команда, которая занята делом и молчит: вывода нет, база не трогается."""
    return [sys.executable, "-c",
            "import time\nt=time.time()\nwhile time.time()-t<%d: pass" % секунд]


def test_busy_silent_process_is_not_called_a_hang(tmp_path, capsys):
    """Процессор занят — это работа, и подсказки «не ждать» быть не должно."""
    б = база(tmp_path)
    команда = _крутит_процессор(12) + [
        "DESIGNER", "/F", str(б), "/N", "Admin", "/DumpCfg", "a.cf",
        "/DisableStartupDialogs", "/Out", str(tmp_path / "log.txt")]
    код, отчёт = mod.запустить(команда, ответы={"база-одноразовая"}, таймаут=60,
                               порог_подозрения=3)
    напечатано = capsys.readouterr().out
    assert код == 0, отчёт
    assert "модальный диалог" not in напечатано + отчёт, напечатано
    assert "Не ждать" not in напечатано + отчёт, напечатано
    assert "работает" in напечатано, напечатано


def test_busy_process_killed_by_timeout_is_not_called_a_hang(tmp_path):
    """Истёк таймаут у работающего процесса — совет «увеличить таймаут»."""
    б = база(tmp_path)
    команда = _крутит_процессор(30) + [
        "DESIGNER", "/F", str(б), "/N", "Admin", "/DumpCfg", "a.cf",
        "/DisableStartupDialogs", "/Out", str(tmp_path / "log.txt")]
    код, отчёт = mod.запустить(команда, ответы={"база-одноразовая"}, таймаут=5,
                               порог_подозрения=2)
    assert код == 3
    assert "модальный диалог" not in отчёт, отчёт
    assert "--таймаут" in отчёт, отчёт


def test_cpu_time_of_a_running_process_is_measurable():
    """Процессорное время процесса снимается в этой ОС, а не молча None."""
    import subprocess
    п = subprocess.Popen(_крутит_процессор(3))
    try:
        import time
        time.sleep(1.5)
        снято = mod._процессорное_время(п.pid)
    finally:
        п.kill(); п.wait()
    if os.name == "nt" or sys.platform.startswith("linux"):
        assert снято is not None and снято > 0.3, снято
