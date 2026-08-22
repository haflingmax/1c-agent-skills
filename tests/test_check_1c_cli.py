"""Регрессия проверяльщика командной строки.

Каждый тест соответствует дефекту из docs/plan.md, подтверждённому запуском.
Запуск: python -m pytest tests/test_check_1c_cli.py -v
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "1c-build-and-db" / "scripts" / "check-1c-cli.py"

spec = importlib.util.spec_from_file_location("check_1c_cli", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["check_1c_cli"] = mod
spec.loader.exec_module(mod)

CATALOG = mod.load_catalog()


def problems(line):
    return mod.check(line, CATALOG)[0]


def notes(line):
    return mod.check(line, CATALOG)[1]


def exit_code(line):
    """Код возврата настоящего запуска: навык обещает «0 — можно запускать»."""
    return subprocess.run([sys.executable, str(SCRIPT), line]).returncode


def test_d13_invented_key_is_rejected():
    """Д-13: /DumpCfgToFile не существует и не должен проходить за /DumpCfg."""
    out = problems("1cv8 DESIGNER /F d:/base /DumpCfgToFile d:/x.cf "
                   "/DisableStartupDialogs /Out d:/l.log")
    assert any("DumpCfgToFile" in p for p in out), out


def test_d13_glued_value_key_still_works():
    """Слитные ключи со значением остаются законными: /L<код языка>.

    Законными — значит не блокируются. Предупреждение при этом выдаётся, см.
    test_glued_prefix_costs_a_note_on_legit_keys: отличить /Lru от выдуманного
    /LoadCfgFromFile механически нельзя, и цена честности платится здесь.
    """
    assert problems("1cv8 DESIGNER /F d:/base /Lru /DumpCfg d:/x.cf "
                    "/DisableStartupDialogs /Out d:/l.log") == []


# Четыре выдуманных ключа, каждый из которых начинается со слитного: /P, /N,
# /O, /WSA. До правки все проходили молча с кодом 0 — то есть главное
# обещание проверяльщика («ловит выдуманный ключ») держалось только для ключей,
# не начинающихся со слитного.
#
# /LoadCfgFromFile раньше был в этом списке пятым, потому что старый known_key
# искал совпадение только среди двенадцати glued-ключей и ложно резолвил его
# в /L. Н-02: платформа берёт самое длинное совпадение среди ВСЕХ ключей —
# для /LoadCfgFromFile это /LoadCfg, не glued, и хвост «FromFile» уходит не в
# значение, а в позиционный аргумент. Это уже проверено запуском (платформа
# отвечает кодом 1, «Файл не обнаружен»), поэтому теперь у него другая пара —
# см. INVENTED_LONGEST_MATCH_BLOCKS и test_longest_match_off_glued_prefix_blocks.
INVENTED_ON_GLUED = [
    ("/Publish", "/P"),
    ("/NewConfiguration", "/N"),
    ("/OptimizeDatabase", "/O"),
    ("/WSAuthentication", "/WSA"),
]


def line_with(key):
    return ("1cv8 DESIGNER /F d:/base %s d:/x.cf /DisableStartupDialogs "
            "/Out d:/l.log" % key)


@pytest.mark.parametrize("key,canon", INVENTED_ON_GLUED)
def test_glued_prefix_invented_key_warns_and_does_not_block(key, canon):
    """Выдуманный ключ на слитном префиксе называется вслух, но не блокируется.

    Блокировать нельзя: /Publish и /Padmin, /LoadCfgFromFile и /Lru устроены
    одинаково — слитный ключ плюс буквы. Проверено запуском, что законная
    половина работает (/Lru + /DumpCfg создал файл), а значит запрет остановил
    бы верное. Правило 11 архитектуры: не показал — не блокируй.
    """
    assert problems(line_with(key)) == [], problems(line_with(key))
    out = notes(line_with(key))
    assert any(key in n and canon in n for n in out), out
    assert exit_code(line_with(key)) == 0


@pytest.mark.parametrize("key", ["/Lru", "/Padmin"])
def test_glued_prefix_costs_a_note_on_legit_keys(key):
    """Цена решения: законный слитный ключ тоже получает предупреждение.

    Это осознанно. Эвристика «хвост похож на имя ключа» не спасает: у /Publish
    хвост «ublish», у /Padmin — «admin», оба строчные и одной длины.
    """
    assert problems(line_with(key)) == [], problems(line_with(key))
    assert any(key in n for n in notes(line_with(key))), notes(line_with(key))
    assert exit_code(line_with(key)) == 0


def test_invented_key_off_glued_prefix_still_blocks():
    """Защита точным совпадением на месте: /DumpCfgToFile — ошибка и код 1."""
    line = line_with("/DumpCfgToFile")
    assert any("DumpCfgToFile" in p for p in problems(line)), problems(line)
    assert exit_code(line) == 1


def test_known_key_matches_platform_longest_match():
    """Н-02: платформа берёт самое длинное совпадение среди ВСЕХ ключей.

    Проверено запуском: /LoadCfgFromFile платформа разбирает как /LoadCfg
    с позиционным аргументом FromFile, а не как /L со значением.
    """
    keys = CATALOG["ключи"]
    assert mod.known_key("/LoadCfgFromFile", keys) == "/LoadCfg"
    assert mod.known_key("/DumpCfgToFile", keys) == "/DumpCfg"
    assert mod.known_key("/Lru", keys) == "/L"


# Оба резолвятся в НЕ-glued ключ (/LoadCfg, /DumpCfg): хвост уходит не в
# значение, а в позиционный аргумент, который платформа отправляет сама.
# Проверено запуском дважды и оба раза неверно: /DumpCfgToFile выгружает
# конфигурацию не в тот файл — тихая порча (docs/evidence/
# 2026-08-22-blocking-rules.md), /LoadCfgFromFile падает кодом 1, «Файл не
# обнаружен» (шаг 1 задачи 3, .superpowers/sdd/2026-08-23-core-remediation/
# task-3-brief.md). В обоих случаях платформа доказанно не делает того, что
# написано в команде — правило 11 требует блокировки, а не предупреждения.
INVENTED_LONGEST_MATCH_BLOCKS = [
    ("/LoadCfgFromFile", "/LoadCfg"),
    ("/DumpCfgToFile", "/DumpCfg"),
]


@pytest.mark.parametrize("key,canon", INVENTED_LONGEST_MATCH_BLOCKS)
def test_longest_match_off_glued_prefix_blocks(key, canon):
    """Н-02: хвост-позиционный-аргумент — это не то же самое, что
    хвост-значение (test_glued_prefix_invented_key_warns_and_does_not_block),
    и различить их теперь можно: по признаку glued резолвнутого ключа.
    """
    line = line_with(key)
    out = problems(line)
    assert any(key in p and canon in p for p in out), out
    assert exit_code(line) == 1


def test_glued_flag_is_present_and_small():
    """Признак glued проставлен и стоит ровно у 12 ключей."""
    glued = [k for k, v in CATALOG["ключи"].items() if v.get("glued")]
    assert len(glued) == 12, glued
    assert "/L" in glued and "/DumpCfg" not in glued, glued


def test_glued_prefix_collision_picks_longest_match():
    """/O и /OIDA оба glued; /OIDAOff обязан разрешиться в /OIDA, а не в /O.

    known_key перебирает keys.items() и обязан брать самое длинное совпадение,
    а не первое попавшееся — иначе более короткий glued-ключ ложно перехватывает
    значение более длинного.
    """
    assert mod.known_key("/OIDAOff", CATALOG["ключи"]) == "/OIDA"


def test_d14_env_var_is_allowed():
    """Д-14: %TEMP% — законный переносимый путь."""
    assert problems("1cv8 DESIGNER /F d:/base /LoadCfg d:/n.cf "
                    "/DisableStartupDialogs /Out %TEMP%/load.log "
                    "/DumpResult %TEMP%/rc.txt") == []


def test_d15_real_name_with_vash_is_allowed():
    """Д-15: «Ваш Дом» — настоящее название организации."""
    assert problems('1cv8 DESIGNER /F "d:/Базы/ООО Ваш Дом" /LoadCfg d:/n.cf '
                    "/DisableStartupDialogs /Out d:/l.log /DumpResult d:/rc.txt") == []


def test_d16_lowercase_key_is_allowed():
    """Д-16: ключи 1С регистронезависимы, проверено запуском."""
    assert problems("1cv8 DESIGNER /F d:/base /loadcfg d:/n.cf "
                    "/DisableStartupDialogs /Out d:/l.log /DumpResult d:/rc.txt") == []


FOREIGN = "ibcmd infobase config load --db-path=d:/base --file=d:/new.cf"


def test_d17_foreign_tool_is_not_judged():
    """Д-17: ibcmd не 1cv8; скрипт не судит чужой инструмент и не запрещает его.

    Прежняя редакция теста требовала ровно одну запись в problems — то есть
    закрепляла код возврата 1 на инструменте, который рекомендует наш же
    рецепт (references/load-configuration.md, шаг 3). Граница компетенции —
    это замечание, а не приговор.
    """
    assert problems(FOREIGN) == [], problems(FOREIGN)
    out = notes(FOREIGN)
    assert len(out) == 1, out
    assert "вне компетенции" in out[0], out


def test_d17_foreign_tool_returns_zero():
    """SKILL.md обещает «код возврата 0 — можно запускать». Проверяем запуском."""
    assert exit_code(FOREIGN) == 0


def test_c1_ib_connection_string_sets_the_base():
    """/IBConnectionString задаёт базу наравне с /F.

    М-16: докстрока и проверка раньше расходились — докстрока ссылалась на
    запуск DESIGNER + /DumpCfg, а сама проверка гоняла ENTERPRISE без
    /DumpCfg вовсе, то есть заявляла одно, а проверяла другое.

    Проверено запуском на 8.3.27.2325: DESIGNER /IBConnectionString
    "File=D:/1C/base/trade;" /DumpCfg создал файл того же размера, что и
    выгрузка через /F (docs/evidence/2026-08-22-blocking-rules.md, случай
    «строка-соединения»). Теперь проверка гоняет ровно этот запуск.
    """
    assert problems('1cv8 DESIGNER /IBConnectionString "File=d:/base;" '
                    "/DumpCfg d:/x.cf /DisableStartupDialogs /Out d:/l.log") == []


def test_c1_lowercase_base_key_is_allowed():
    """Регистр не важен и для ключа базы: /f — та же база, что /F."""
    assert problems("1cv8 DESIGNER /f d:/base /dumpcfg d:/out.cf "
                    "/disablestartupdialogs") == []


def test_no_base_still_blocks():
    """Незаданная база остаётся ошибкой: платформа отвечает «Неопределена
    информационная база», код 1, файла нет — проверено запуском."""
    out = problems("1cv8 DESIGNER /DumpCfg d:/x.cf /DisableStartupDialogs /Out d:/l.log")
    assert any("не задана база" in p for p in out), out


def test_no_mode_still_blocks():
    """Неуказанный режим остаётся ошибкой: «Неопределен режим запуска», код 1."""
    out = problems("1cv8 /F d:/base /DumpCfg d:/x.cf /DisableStartupDialogs /Out d:/l.log")
    assert any("режим запуска" in p for p in out), out


def test_config_word_is_not_a_recognized_mode():
    """М-14: CONFIG был в MODE_WORDS, хотя не документирован ни как режим
    запуска 8.3.27, ни в тексте ошибки, ни у единого ключа каталога.

    Раздел 7.3.3 руководства администратора называет CONFIG, но только как
    замену, которую платформа выполняет САМА при автоподборе версии для
    запуска настоящего 1С:Предприятия 8.0 (/AppAutoCheckVersion) — это
    внутренний механизм для другого исполняемого файла, а не режим запуска,
    который стоит писать в команде для 8.3.27. Раньше CONFIG в MODE_WORDS
    молча гасил «не указан режим запуска» там, где такого режима у 8.3.27
    нет вовсе.
    """
    out = problems("1cv8 CONFIG /F d:/base /DumpCfg d:/x.cf "
                   "/DisableStartupDialogs /Out d:/l.log")
    assert any("режим запуска" in p for p in out), out


def test_alien_mode_key_inside_designer_is_only_a_note():
    """Ключ чужого режима внутри пакетного DESIGNER не блокируется.

    Проверено запуском: DESIGNER /F <база> /UsePrivilegedMode /DumpCfg
    отработал, файл создан и совпал по размеру с обычной выгрузкой. Правило 11
    архитектуры: не показал — не блокируй.
    """
    line = ("1cv8 DESIGNER /F d:/base /UsePrivilegedMode /DumpCfg d:/x.cf "
            "/DisableStartupDialogs /Out d:/l.log")
    assert problems(line) == [], problems(line)
    assert any("UsePrivilegedMode" in n for n in notes(line)), notes(line)


def test_alien_option_is_only_a_note():
    """Опция не от этого ключа не блокируется: платформа её приняла.

    Проверено запуском: DESIGNER /F <база> /DumpCfg <файл> -Format Hierarchical
    отработал, файл создан и побайтно того же размера, что и без опции.
    """
    line = ("1cv8 DESIGNER /F d:/base /DumpCfg d:/x.cf -Format Hierarchical "
            "/DisableStartupDialogs /Out d:/l.log")
    assert problems(line) == [], problems(line)
    assert any("-Format" in n for n in notes(line)), notes(line)


def test_placeholder_still_blocks():
    """Заглушка версии остаётся ошибкой: путь не существует."""
    assert any("8.3.xx" in p for p in problems(
        r'"C:\Program Files\1cv8\8.3.xx.yyyy\bin\1cv8.exe" DESIGNER /F d:/base '
        "/LoadCfg d:/n.cf /DisableStartupDialogs /Out d:/l.log"))


def test_wrong_mode_still_blocks():
    """Пакетный ключ конфигуратора вне DESIGNER остаётся ошибкой.

    Проверено запуском: ENTERPRISE /F <база> /LoadCfg <файл>
    /DisableStartupDialogs не загрузил ничего — платформа открыла сеанс и не
    вернула управление, процесс убит по таймауту 60 секунд, журнал пуст,
    /DumpResult не создан.
    """
    assert any("режиме" in p for p in problems(
        "1cv8 ENTERPRISE /F d:/base /LoadCfg d:/n.cf /Out d:/l.log"))


def test_catalog_completeness_against_source():
    """Н-07, Н-08: состав каталога сверяется с приложением 7 программно.

    Источник — _its/cmdline/its-pril7-full.json. Если выгрузки нет на машине,
    тест пропускается: каталог _its/ под gitignore и у пользователя его нет.
    """
    import pytest
    src = ROOT / "_its" / "cmdline" / "its-pril7-full.json"
    if not src.exists():
        pytest.skip("выгрузка ИТС недоступна: каталог _its/ под gitignore")
    keys = CATALOG["ключи"]
    assert "/@" in keys, "документированный ключ /@ (раздел 7.3.11) отсутствует"
    assert isinstance(keys["/DumpResult"]["modes"], list), "режим обязан быть списком"
    assert len(keys["/DumpResult"]["modes"]) >= 2, (
        "/DumpResult описан в двух режимах: 7.2.3 и 7.4.17")


AT_KEY_NOT_FIRST = ("1cv8 DESIGNER /F d:/base /DumpCfg d:/x.cf /@ d:/cmd.txt "
                    "/DisableStartupDialogs /Out d:/l.log")


def test_at_key_not_first_only_warns():
    """Н-08 (найдено повторным ревью): /@ добавили в каталог, но не хватало
    правила позиции — команда с /@ не первым ключом проходила без единого
    замечания, хотя документация называет это неопределённым поведением.

    Раздел 7.3.11 руководства администратора, дословно: «Команда /@ должна
    быть первой или единственной командой командной строки запуска
    приложения. Если команда /@ указана не первой ‑ поведение является
    неопределенным.» «Неопределено» — не «запрещено»: платформой это не
    проверено запуском, поэтому правило 11 архитектуры («блокировать только
    доказанно неверное») требует предупреждения, а не ошибки.
    """
    assert problems(AT_KEY_NOT_FIRST) == [], problems(AT_KEY_NOT_FIRST)
    out = notes(AT_KEY_NOT_FIRST)
    assert any("/@" in n and "не первым" in n for n in out), out
    assert exit_code(AT_KEY_NOT_FIRST) == 0


@pytest.mark.parametrize("line", [
    # /@ — первый /-ключ команды (перед ним только слово режима, не ключ).
    "1cv8 DESIGNER /@ d:/cmd.txt /F d:/base /DisableStartupDialogs",
    # /@ — единственный ключ команды вообще (условие «или единственной»).
    "1cv8 /@ d:/cmd.txt",
])
def test_at_key_first_is_clean(line):
    """Две законные команды с /@ первым (или единственным) ключом — правило
    не должно заводить новую блокировку и не должно предупреждать про
    позицию: по разделу 7.3.11 это ровно тот случай, который документация
    разрешает.
    """
    assert not any("/@" in n and "не первым" in n for n in notes(line)), notes(line)


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_flag_prints_docstring_and_returns_zero(flag):
    """М-25: скрипт не отвечал на --help вовсе — argv[0] == "--help" уходил
    как обычная команда на проверку, tool.startswith("1cv8") давал False, и
    вместо помощи печаталось «--help вне компетенции проверяльщика».
    """
    out = subprocess.run([sys.executable, str(SCRIPT), flag],
                         capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    assert out.returncode == 0, out
    assert "вне компетенции" not in out.stdout, out.stdout
    assert "Проверка командной строки" in out.stdout, out.stdout
