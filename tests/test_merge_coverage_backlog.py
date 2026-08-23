"""Регрессия сведения перечня тем (РАЗБОР-2а).

Проверяется сама проверка: она обязана ловить неразобранную единицу,
причину не из перечня, тему без опоры, повтор темы, просочившийся вердикт
и предложение по раскладке без названного возражения.

Запуск: python -m pytest tests/test_merge_coverage_backlog.py -v
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "merge-coverage-backlog.py"

spec = importlib.util.spec_from_file_location("merge_coverage_backlog", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["merge_coverage_backlog"] = mod
spec.loader.exec_module(mod)


@pytest.fixture
def ref(tmp_path):
    """Живой файл, на который можно сослаться опорой."""
    d = tmp_path / "cc-1c-skills" / ".claude" / "skills" / "cf-edit"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("тело", encoding="utf-8")
    return tmp_path


SUPPORT = "cc-1c-skills/.claude/skills/cf-edit/SKILL.md:12"


def section(**over):
    d = {
        "раздел": "1c-build-and-db",
        "единицы": [{"единица": "cf-edit", "в_охвате": True, "почему_нет": "",
                     "темы_единицы": ["правка корня конфигурации"]}],
        "темы": [{"тема": "правка корня конфигурации",
                  "о_чём": "Как менять свойства конфигурации, не ломая состав.",
                  "откуда": ["cf-edit"], "опора": SUPPORT}],
        "замечено_сверх": [],
    }
    d.update(over)
    return d


# --- годный выход раздела ---------------------------------------------------

def test_good_section_has_no_notes(ref):
    assert mod.check_section_file(section(), ["cf-edit"], ref) == []


# --- полнота: единица не может потеряться -----------------------------------

def test_unanalysed_unit_is_reported(ref):
    notes = mod.check_section_file(section(), ["cf-edit", "db-run"], ref)
    assert any("не разобраны 1" in n and "db-run" in n for n in notes), notes


def test_alien_unit_is_reported(ref):
    """Разобрана единица из чужого раздела — признак сбитой нарезки."""
    notes = mod.check_section_file(section(), [], ref)
    assert any("не из этого раздела" in n for n in notes), notes


# --- причина отказа берётся из перечня --------------------------------------

def test_out_of_scope_reason_must_be_from_the_list(ref):
    d = section(единицы=[{"единица": "cf-edit", "в_охвате": False,
                          "почему_нет": "не пригодилось", "темы_единицы": []}])
    notes = mod.check_section_file(d, ["cf-edit"], ref)
    assert any("не из перечня" in n for n in notes), notes


def test_in_scope_unit_must_not_carry_a_reason(ref):
    d = section(единицы=[{"единица": "cf-edit", "в_охвате": True,
                          "почему_нет": "БСП", "темы_единицы": []}])
    notes = mod.check_section_file(d, ["cf-edit"], ref)
    assert any("заполнено «почему_нет»" in n for n in notes), notes


def test_excluded_unit_must_not_produce_topics(ref):
    """Единица вне охвата тем не порождает — иначе правило охвата обойдено."""
    d = section(единицы=[{"единица": "cf-edit", "в_охвате": False, "почему_нет": "БСП",
                          "темы_единицы": ["правка корня конфигурации"]}])
    notes = mod.check_section_file(d, ["cf-edit"], ref)
    assert any("вне охвата, но названы темы" in n for n in notes), notes


# --- темы -------------------------------------------------------------------

def test_duplicate_topic_is_reported(ref):
    """Повтор в перечне значит, что сведение не доведено.

    Ради сведения повторов агент и получает весь раздел разом: одиннадцать
    единиц про формы называют одну тему разными словами.
    """
    t = section()["темы"][0]
    d = section(темы=[t, dict(t)])
    notes = mod.check_section_file(d, ["cf-edit"], ref)
    assert any("названа дважды" in n for n in notes), notes


def test_topic_without_support_is_reported(ref):
    d = section(темы=[{"тема": "т", "о_чём": "о", "откуда": ["cf-edit"], "опора": ""}])
    notes = mod.check_section_file(d, ["cf-edit"], ref)
    assert any("в опоре нет пути" in n for n in notes), notes


def test_topic_support_must_resolve(ref):
    d = section(темы=[{"тема": "т", "о_чём": "о", "откуда": ["cf-edit"],
                       "опора": "cc-1c-skills/.claude/skills/призрак/SKILL.md:1"}])
    notes = mod.check_section_file(d, ["cf-edit"], ref)
    assert any("не ведёт к файлу" in n for n in notes), notes


def test_topic_must_name_its_origin(ref):
    d = section(темы=[{"тема": "т", "о_чём": "о", "откуда": [], "опора": SUPPORT}])
    notes = mod.check_section_file(d, ["cf-edit"], ref)
    assert any("не сказано, из каких единиц" in n for n in notes), notes


def test_topic_origin_must_exist_in_the_section(ref):
    d = section(темы=[{"тема": "т", "о_чём": "о", "откуда": ["призрак"], "опора": SUPPORT}])
    notes = mod.check_section_file(d, ["cf-edit"], ref)
    assert any("призрак" in n for n in notes), notes


def test_unit_cannot_name_a_topic_absent_from_the_list(ref):
    d = section(единицы=[{"единица": "cf-edit", "в_охвате": True, "почему_нет": "",
                          "темы_единицы": ["тема, которой нет"]}])
    notes = mod.check_section_file(d, ["cf-edit"], ref)
    assert any("которой нет в перечне" in n for n in notes), notes


def test_verdict_in_a_topic_is_caught(ref):
    """Перечень тем описывает обязанность набора, а не советует брать чужое."""
    d = section(темы=[{"тема": "правка корня", "о_чём": "Стоит взять целиком.",
                       "откуда": ["cf-edit"], "опора": SUPPORT}])
    notes = mod.check_section_file(d, ["cf-edit"], ref)
    assert any("вердикт" in n for n in notes), notes


def test_domain_wording_is_not_a_verdict(ref):
    """Правило вердикта берётся из соседнего инструмента вместе с его защитой
    от ложных срабатываний на доменном языке 1С."""
    d = section(
        единицы=[{"единица": "cf-edit", "в_охвате": True, "почему_нет": "",
                  "темы_единицы": ["перенос вставок расширения"]}],
        темы=[{"тема": "перенос вставок расширения",
               "о_чём": "Как проверить статус переноса вставок.",
               "откуда": ["cf-edit"], "опора": SUPPORT}])
    assert mod.check_section_file(d, ["cf-edit"], ref) == []


# --- единицы вне раскладки --------------------------------------------------

def outside(**over):
    d = {
        "единицы": [{"единица": "cf-edit", "почему_не_легла": "не про 1С",
                     "раздел": "", "пояснение": "транскрибация аудио", "опора": SUPPORT}],
        "предложения": [],
    }
    d.update(over)
    return d


def test_good_outside_has_no_notes(ref):
    assert mod.check_outside_file(outside(), ["cf-edit"], ref) == []


def test_placed_unit_must_name_a_real_section(ref):
    d = outside(единицы=[{"единица": "cf-edit", "почему_не_легла": "ложится в существующий",
                          "раздел": "1c-libraries-bsp", "пояснение": "п", "опора": SUPPORT}])
    notes = mod.check_outside_file(d, ["cf-edit"], ref)
    assert any("не из пятнадцати" in n for n in notes), notes


def test_section_filled_without_placement_is_reported(ref):
    d = outside(единицы=[{"единица": "cf-edit", "почему_не_легла": "не про 1С",
                          "раздел": "1c-queries", "пояснение": "п", "опора": SUPPORT}])
    notes = mod.check_outside_file(d, ["cf-edit"], ref)
    assert any("раздел заполнен" in n for n in notes), notes


def test_proposal_without_objection_is_reported(ref):
    """Предложение без возражения владелец взвесить не сможет.

    У проекта есть решение не заводить навыки сверх раскладки: каждый лишний
    оплачивается местом в каталоге Codex. Предложение, умалчивающее об этом,
    выглядит бесплатным.
    """
    d = outside(предложения=[{"предложение": "раздел про подсистемы",
                              "основание": "четыре единицы не легли", "против": ""}])
    notes = mod.check_outside_file(d, ["cf-edit"], ref)
    assert any("не названо, что говорит против" in n for n in notes), notes


def test_proposal_with_objection_passes(ref):
    d = outside(предложения=[{"предложение": "раздел про подсистемы",
                              "основание": "четыре единицы не легли",
                              "против": "решение 11: каждый навык оплачивается каталогом"}])
    assert mod.check_outside_file(d, ["cf-edit"], ref) == []


# --- отказ вместо пустого файла ---------------------------------------------

def test_refuses_without_outputs(tmp_path):
    (tmp_path / "1c-queries.json").write_text(
        json.dumps({"записи": [{"единица": "x"}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path), "--ref", str(tmp_path),
                        "--out-json", str(tmp_path / "o.json"),
                        "--out-md", str(tmp_path / "o.md")],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "out-*.json" in (r.stdout + r.stderr)
    assert not (tmp_path / "o.json").exists()


def test_unanalysed_section_is_reported(tmp_path, ref):
    (tmp_path / "1c-queries.json").write_text(
        json.dumps({"записи": [{"единица": "x"}]}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "1c-extensions.json").write_text(
        json.dumps({"записи": [{"единица": "y"}]}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "out-1c-queries.json").write_text(
        json.dumps(section(раздел="1c-queries",
                           единицы=[{"единица": "x", "в_охвате": True,
                                     "почему_нет": "", "темы_единицы": []}],
                           темы=[]), ensure_ascii=False), encoding="utf-8")
    _, problems = mod.merge(tmp_path, ref)
    assert any("1c-extensions не разобран вовсе" in p for p in problems), problems
