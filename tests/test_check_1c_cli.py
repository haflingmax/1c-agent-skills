"""Регрессия проверяльщика командной строки.

Каждый тест соответствует дефекту из docs/plan.md, подтверждённому запуском.
Запуск: python -m pytest tests/test_check_1c_cli.py -v
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

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
    """Слитные ключи со значением остаются законными: /L<код языка>."""
    assert problems("1cv8 DESIGNER /F d:/base /Lru /DumpCfg d:/x.cf "
                    "/DisableStartupDialogs /Out d:/l.log") == []


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

    Проверено запуском на 8.3.27.2325: DESIGNER /IBConnectionString
    "File=D:/1C/base/trade;" /DumpCfg создал файл того же размера, что и
    выгрузка через /F (docs/evidence/2026-08-22-blocking-rules.md).
    """
    assert problems('1cv8 ENTERPRISE /IBConnectionString "File=d:/base;" '
                    "/DisableStartupDialogs") == []


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
