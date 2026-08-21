"""Регрессия проверяльщика командной строки.

Каждый тест соответствует дефекту из docs/plan.md, подтверждённому запуском.
Запуск: python -m pytest tests/test_check_1c_cli.py -v
"""
import importlib.util
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


def test_d17_foreign_tool_is_not_judged():
    """Д-17: ibcmd не 1cv8; скрипт не судит чужой инструмент."""
    out = problems("ibcmd infobase config load --db-path=d:/base --file=d:/new.cf")
    assert len(out) == 1, out
    assert "вне компетенции" in out[0], out


def test_placeholder_still_blocks():
    """Заглушка версии остаётся ошибкой: путь не существует."""
    assert any("8.3.xx" in p for p in problems(
        r'"C:\Program Files\1cv8\8.3.xx.yyyy\bin\1cv8.exe" DESIGNER /F d:/base '
        "/LoadCfg d:/n.cf /DisableStartupDialogs /Out d:/l.log"))


def test_wrong_mode_still_blocks():
    """Ключ не из этого режима остаётся ошибкой."""
    assert any("режиме" in p for p in problems(
        "1cv8 ENTERPRISE /F d:/base /LoadCfg d:/n.cf /Out d:/l.log"))
