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


def заглушка(tmp_path, тело, имя="подставной-1cv8.cmd"):
    """Подставная «платформа»: делает ровно то, что нужно проверить."""
    ф = tmp_path / имя
    ф.write_text("@echo off\r\n" + тело, encoding="ascii", newline="")
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
    тихий = заглушка(tmp_path, "ping -n 31 127.0.0.1 >nul\r\n")
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
    пустышка = заглушка(tmp_path, "exit /b 0\r\n")
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
    эхо = заглушка(tmp_path, "echo %3\r\n")
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
    тихий = заглушка(tmp_path, "ping -n 31 127.0.0.1 >nul\r\n")
    команда = ('%s DESIGNER /F "%s" /N Admin /P"" /LoadCfg a.cf '
               '/UpdateDBCfg -Dynamic- /DisableStartupDialogs /Out log.txt'
               % (тихий, б))
    mod.запустить(команда, ответы={"база-одноразовая"}, таймаут=6,
                  порог_подозрения=2)
    напечатано = capsys.readouterr().out
    assert "модальный диалог" in напечатано, (
        "диагноз не напечатан до конца ожидания: %r" % напечатано)
