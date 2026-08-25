"""Регрессия механического слоя описи данных референсов (РАЗБОР-1б).

Навыки описаны отдельно (`test_build_reference_registry.py`). Здесь — всё
остальное содержимое обоих наборов: спецификации `docs/`, правила `rules/`,
справочники внутри навыков, обвязка, скрипты и наборы тестовых случаев.

Слой механический: ни выжимки, ни отнесения к разделу, ни решения о судьбе
объекта. Всё извлекается из файлов и воспроизводится перезапуском.

Запуск: python -m pytest tests/test_build_reference_data_registry.py -v
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "build-reference-data-registry.py"
REF = ROOT / "_ref"

spec = importlib.util.spec_from_file_location("build_reference_data_registry", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["build_reference_data_registry"] = mod
spec.loader.exec_module(mod)

needs_ref = pytest.mark.skipif(not REF.is_dir(), reason="_ref/ под gitignore")


# --- разбор markdown --------------------------------------------------------

def test_title_comes_from_first_heading():
    assert mod.md_title("# 1C Form.xml Format Specification\n\nтекст\n") \
        == "1C Form.xml Format Specification"


def test_title_skips_frontmatter():
    """У файлов rules/ сверху фронтматтер с путями, а заголовка может не быть."""
    text = '---\npaths:\n  - "**/*.bsl"\n---\n\n# Стандарты кода\n\nтело\n'
    assert mod.md_title(text) == "Стандарты кода"


def test_title_absent_is_empty_not_a_crash():
    assert mod.md_title('---\npaths:\n  - "x"\n---\n\nпросто текст\n') == ""


def test_lead_is_the_first_real_paragraph():
    """Первый абзац после заголовка — единственное, что берётся из тела.

    Больше механический слой брать не вправе: пересказ — уже суждение.
    """
    text = ("# Заголовок\n\nСпецификация формата управляемых форм.\n"
            "Составлена на основе анализа 7723 форм.\n\n## Раздел\n")
    lead = mod.md_lead(text)
    assert lead.startswith("Спецификация формата")
    assert "7723" in lead
    assert "## Раздел" not in lead


def test_lead_ignores_horizontal_rule():
    assert mod.md_lead("# Ш\n\n---\n\nНастоящий текст.\n") == "Настоящий текст."


def test_headings_are_counted_below_the_title():
    text = "# Т\n\n## А\n\n### Б\n\n## В\n"
    assert mod.md_headings(text) == 3


# --- разбор скриптов --------------------------------------------------------

def test_script_header_skips_shebang():
    text = ("#!/usr/bin/env python3\n"
            "# cf-edit v1.23 — Edit 1C configuration root\n"
            "# Source: https://example/repo\n\nimport os\n")
    header = mod.script_header(text)
    assert "cf-edit v1.23" in header
    assert "#!/usr/bin" not in header


def test_script_header_reads_powershell_comments():
    assert "Публикует базу" in mod.script_header("<#\nПубликует базу\n#>\nparam()\n")


def test_platform_call_is_detected_by_the_binary_name():
    """Зовёт ли объект платформу — факт, а не суждение: ищем 1cv8/ibcmd."""
    assert mod.calls_platform('subprocess.run(["1cv8", "DESIGNER"])')
    assert mod.calls_platform("& ibcmd infobase config load")
    assert not mod.calls_platform("import xml.etree.ElementTree as ET")


def test_cli_flags_are_extracted_from_both_languages():
    py = "p.add_argument('--ConfigPath')\np.add_argument('--Operation')\n"
    assert mod.cli_flags(py) == ["--ConfigPath", "--Operation"]
    ps = "param(\n  [string]$ConfigPath,\n  [switch]$NoValidate\n)\n"
    assert mod.cli_flags(ps) == ["-ConfigPath", "-NoValidate"]


# --- спаривание одноимённых файлов docs/ ------------------------------------

def test_docs_pair_by_identical_filename():
    """`docs/` форкнут так же, как навыки: одно имя — две версии."""
    assert mod.pair_key("docs", "1c-form-spec.md") == "docs/1c-form-spec.md"


# --- отказ вместо пустой описи ---------------------------------------------

def test_refuses_without_ref(tmp_path):
    r = subprocess.run([sys.executable, str(SCRIPT), "--ref", str(tmp_path / "нет")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "_ref" in (r.stdout + r.stderr)


# --- на живой выгрузке ------------------------------------------------------

@needs_ref
def test_every_class_is_present():
    reg = mod.build(REF)
    got = {c["класс"] for c in reg["классы"]}
    assert got == {"docs", "rules", "справочники навыков", "обвязка",
                   "скрипты навыков", "тесты"}, got


@needs_ref
def test_every_object_has_a_живой_path():
    reg = mod.build(REF)
    for o in reg["объекты"]:
        assert (REF / o["путь"]).is_file(), o["путь"]


@needs_ref
def test_counts_match_the_declared_scope():
    """Числа берутся из обхода, а не переписываются из плана."""
    reg = mod.build(REF)
    by = {c["класс"]: c["файлов"] for c in reg["классы"]}
    assert by["docs"] == 79, by
    assert by["rules"] == 35, by
    assert by["справочники навыков"] == 116, by


@needs_ref
def test_docs_pairs_are_symmetric():
    reg = mod.build(REF)
    by = {(o["набор"], o["путь"]): o for o in reg["объекты"]}
    for o in reg["объекты"]:
        if not o.get("пара"):
            continue
        other = by[(o["пара"]["набор"], o["пара"]["путь"])]
        assert other.get("пара"), o["путь"]
        assert other["пара"]["путь"] == o["путь"]


@needs_ref
def test_test_families_are_structure_only():
    """По тестам берём структуру семейств, а не содержимое случаев."""
    reg = mod.build(REF)
    fam = reg["семейства_тестов"]
    assert fam, "структура тестовых семейств не собрана"
    for f in fam:
        assert {"набор", "семейство", "файлов"} <= set(f), f
        assert "содержимое" not in f


@needs_ref
def test_registry_is_reproducible():
    assert json.dumps(mod.build(REF), ensure_ascii=False, sort_keys=True) == \
           json.dumps(mod.build(REF), ensure_ascii=False, sort_keys=True)


@needs_ref
def test_no_verdict_fields_in_the_mechanical_layer():
    forbidden = {"вердикт", "решение", "раздел", "выжимка", "суть"}
    for o in mod.build(REF)["объекты"]:
        assert not (forbidden & set(o)), set(o) & forbidden
