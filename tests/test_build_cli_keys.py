"""Разбор приложения 7 сборщиком каталога: M-4 и M-5 финального ревью.

Запуск: python -m pytest tests/test_build_cli_keys.py -v
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BUILDER = ROOT / "tools" / "build-cli-keys.py"
CATALOG = ROOT / "skills" / "1c-build-and-db" / "scripts" / "cli-keys.json"

_spec = importlib.util.spec_from_file_location("build_cli_keys_tests", BUILDER)
mod = importlib.util.module_from_spec(_spec)
sys.modules["build_cli_keys_tests"] = mod
_spec.loader.exec_module(mod)

KEYS = json.loads(CATALOG.read_text(encoding="utf-8"))["ключи"]

TEMPLATE_723 = (
    "1cv8 CREATEINFOBASE <строка соединения> [/AddToList [<имя ИБ>]] "
    "[/UseTemplate <имя файла шаблона>] [/Out <имя файла>] [/L<код языка>] "
    "[/VL<код локализации>] [/O<скорость соединения>] [/DumpResult <имя файла>]"
)


# --- M-5: тихий откат на зашитый шаблон -------------------------------------

def test_missing_template_fails_instead_of_falling_back_silently():
    """M-5: не нашли шаблон — падаем, а не подставляем зашитую копию.

    Воспроизведено до правки: на тексте без шаблона функция молча
    возвращала TEMPLATES[0] и семь имён ключей, ни одного исключения.
    Сегодня результат совпал бы, но изменение формата выгрузки было бы
    замаскировано вместо того, чтобы быть названным.
    """
    with pytest.raises(SystemExit) as e:
        mod.parse_createinfobase_template("совершенно другой текст, шаблона тут нет")
    assert e.value.code == 2


def test_template_is_parsed_when_present():
    entries, template = mod.parse_createinfobase_template(TEMPLATE_723)
    assert template.startswith("CREATEINFOBASE")
    assert dict(entries)["/UseTemplate"] == "<имя файла шаблона>"


# --- M-4: аргумент из шаблона, а не выброшенный -----------------------------

def test_bracket_groups_respect_nesting():
    """«[/AddToList [<имя ИБ>]]» — вложенная группа, по первому «]» её рвать нельзя."""
    groups = mod.bracket_groups("[/AddToList [<имя ИБ>]] [/Out <имя файла>]")
    assert groups == ["/AddToList [<имя ИБ>]", "/Out <имя файла>"]


@pytest.mark.parametrize("name,arg", [
    ("/UseTemplate", "<имя файла шаблона>"),
    ("/AddToList", "[<имя ИБ>]"),
    ("/Out", "<имя файла>"),
    ("/L", "<код языка>"),
    ("/DumpResult", "<имя файла>"),
])
def test_argument_comes_from_its_own_bracket_group(name, arg):
    """M-4: аргумент берётся из своей группы, а не «до следующего ключа».

    Второе цепляло закрывающие скобки соседей: у /L получалось
    «<код языка>] [» вместо «<код языка>» — правка ломала бы уже верные
    значения, добывая новые.
    """
    assert dict(mod.parse_createinfobase_template(TEMPLATE_723)[0])[name] == arg


@pytest.mark.parametrize("name,arg", [
    ("/UseTemplate", "<имя файла шаблона>"),
    ("/AddToList", "[<имя ИБ>]"),
])
def test_catalog_carries_the_documented_argument(name, arg):
    """M-4: у этих двух ключей arg был пуст, хотя источник аргумент документирует."""
    assert KEYS[name]["arg"] == arg


@pytest.mark.parametrize("name,section", [
    ("/IBConnectionString", "7.3.1"),
    ("/AccessToken", "7.3.2"),
])
def test_prose_only_argument_is_named_not_invented(name, section):
    """M-4: чего достать надёжно не выходит — записано поимённо, а не молчанием.

    В 7.3.1 и 7.3.2 синопсис этих ключей — голое имя без единой угловой
    скобки; аргумент описан только прозой следующего абзаца. Превратить прозу
    в значение `arg` значит выдумать форму, которой в источнике нет. Поэтому
    `arg` остаётся пустым (разбор командной строки не меняется), а факт
    записан отдельным полем с цитатой источника.
    """
    entry = KEYS[name]
    assert entry["arg"] == "", "выдуманный синопсис вместо честного пробела"
    assert "arg_прозой" in entry, "пробел не назван"
    assert section in entry["arg_прозой"]
    assert name in mod.ARG_ONLY_IN_PROSE


def test_prose_note_does_not_change_command_parsing():
    """arg_прозой — запись для человека, разбор она не трогает.

    absorbs_glued_tail() смотрит только на `arg` и `glued`. Проверено
    в самой M-4: `/IBConnectionString "File=…"` — замечаний нет, код 0.
    """
    spec = importlib.util.spec_from_file_location(
        "check_1c_cli_m4", ROOT / "skills" / "1c-build-and-db" / "scripts" / "check-1c-cli.py")
    cli = importlib.util.module_from_spec(spec)
    sys.modules["check_1c_cli_m4"] = cli
    spec.loader.exec_module(cli)
    for name in mod.ARG_ONLY_IN_PROSE:
        assert not cli.absorbs_glued_tail(KEYS[name]), (
            "%s стал принимать слитный хвост — источник этого не документирует" % name)
