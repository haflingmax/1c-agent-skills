"""Регрессия механического слоя описи референсов (РАЗБОР-1а).

Слой механический — значит он не имеет права на суждение. Всё, что здесь
проверяется, извлекается из файлов референсных наборов и воспроизводится
перезапуском. Выжимка содержания и отнесение к разделу — читающий слой,
он в этих тестах не участвует.

Запуск: python -m pytest tests/test_build_reference_registry.py -v
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "build-reference-registry.py"
REF = ROOT / "_ref"

spec = importlib.util.spec_from_file_location("build_reference_registry", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["build_reference_registry"] = mod
spec.loader.exec_module(mod)

has_ref = REF.is_dir()
needs_ref = pytest.mark.skipif(not has_ref, reason="_ref/ под gitignore, есть не на каждой машине")


# --- разбор фронтматтера: без него все остальные поля недостоверны ---------

def test_frontmatter_reads_name_and_description():
    """Имя и описание берутся из фронтматтера, а не из имени каталога."""
    text = ("---\nname: cf-edit\ndescription: Точечное редактирование.\n"
            "allowed-tools:\n  - Bash\n---\n\n# тело\n")
    fm = mod.parse_frontmatter(text)
    assert fm["name"] == "cf-edit"
    assert fm["description"] == "Точечное редактирование."


def test_frontmatter_survives_colon_inside_description():
    """Двоеточие внутри описания не должно обрывать значение.

    Ровно на этом обжигался наш собственный проверяльщик (находка Н-01):
    регулярка резала описание по первому двоеточию. Здесь разбор идёт
    по первому двоеточию КЛЮЧА, а остаток строки — значение целиком.
    """
    text = "---\nname: x\ndescription: Делает А: и ещё Б.\n---\nтело\n"
    assert mod.parse_frontmatter(text)["description"] == "Делает А: и ещё Б."


def test_frontmatter_absent_is_not_a_crash():
    """Файл без фронтматтера — не повод падать: это факт про объект."""
    assert mod.parse_frontmatter("# просто заголовок\n") == {}


def test_body_line_count_excludes_frontmatter():
    """Длина тела считается после фронтматтера — сравнивать надо сравнимое."""
    text = "---\nname: x\ndescription: d\n---\nа\nб\nв\n"
    assert mod.body_lines(text) == 3


# --- правило спаривания: 71 навык существует в двух версиях ----------------

def test_pairing_maps_bare_name_to_prefixed():
    """cc-1c-skills зовёт навык «cf-edit», claude-code-skills-1c — «1c-cf-edit».

    Это не совпадение: CHANGELOG второго набора прямо ссылается на первый.
    Без спаривания опись насчитала бы 193 независимых источника там, где их
    заметно меньше.
    """
    assert mod.paired_name("cf-edit") == "1c-cf-edit"
    assert mod.paired_name("db-run") == "1c-db-run"


def test_pairing_does_not_double_prefix():
    """Имя, уже начинающееся с 1c-, второй раз не префиксуется."""
    assert mod.paired_name("1c-bsp-api") == "1c-bsp-api"


# --- отказ без выгрузки: инструмент обязан работать или честно отказываться -

def test_refuses_without_ref_directory(tmp_path):
    """Нет _ref/ — понятное сообщение и код 2, а не пустая опись.

    Правило набора: инструмент, читающий гитигнорную выгрузку, обязан
    работать без неё либо честно отказываться. Молча записать пустой
    реестр — худший из исходов.
    """
    r = subprocess.run([sys.executable, str(SCRIPT), "--ref", str(tmp_path / "нет")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "_ref" in (r.stdout + r.stderr)


# --- то, что проверяется только на живой выгрузке --------------------------

@needs_ref
def test_both_sets_are_found():
    """Оба набора на месте и непустые."""
    reg = mod.build(REF)
    by_set = {s["ключ"]: s for s in reg["наборы"]}
    assert by_set["cc"]["навыков"] > 0
    assert by_set["ccs"]["навыков"] > 0


@needs_ref
def test_total_is_derived_not_inherited():
    """Число объектов берётся из выгрузки, а не наследуется из плана.

    В общем плане стоит «193 объекта» без записанного происхождения.
    Опись обязана назвать своё число; расхождение — факт, а не ошибка.
    """
    reg = mod.build(REF)
    assert reg["всего_навыков"] == sum(s["навыков"] for s in reg["наборы"])


@needs_ref
def test_every_skill_has_a_source_path():
    """У каждой записи есть путь к файлу — иначе её нельзя перепроверить."""
    reg = mod.build(REF)
    for s in reg["навыки"]:
        assert s["путь"], s
        assert (REF / s["путь"]).is_file(), s["путь"]


@needs_ref
def test_pairs_are_symmetric():
    """Спаривание двустороннее: если A указывает на B, то B — на A."""
    reg = mod.build(REF)
    by_key = {(s["набор"], s["имя"]): s for s in reg["навыки"]}
    for s in reg["навыки"]:
        if not s["пара"]:
            continue
        other = by_key[(s["пара"]["набор"], s["пара"]["имя"])]
        assert other["пара"], "%s указывает на %s, обратной ссылки нет" % (s["имя"], s["пара"]["имя"])
        assert other["пара"]["имя"] == s["имя"]


@needs_ref
def test_registry_is_reproducible():
    """Перезапуск даёт тот же результат: механический слой не фантазирует."""
    assert json.dumps(mod.build(REF), ensure_ascii=False, sort_keys=True) == \
           json.dumps(mod.build(REF), ensure_ascii=False, sort_keys=True)


@needs_ref
def test_no_verdict_fields_leak_into_mechanical_layer():
    """В механическом слое не должно быть решения «переносить или нет».

    Владелец просил решать попунктно на следующем этапе. Предварительный
    вердикт в описи заранее сузил бы этот разбор.
    """
    forbidden = {"вердикт", "переносить", "решение", "раздел", "выжимка"}
    for s in mod.build(REF)["навыки"]:
        assert not (forbidden & set(s)), set(s) & forbidden
