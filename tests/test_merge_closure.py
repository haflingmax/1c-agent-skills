"""Регрессия сведения разбора «чем закрывается тема» (РАЗБОР-3).

Главное, что здесь сторожится, — **соразмерность обоснования цене способа**.
Правило объясняется одной фразой; генератор одной фразой объяснить нельзя.
Короткое «нужен скрипт» невозможно оспорить, а значит невозможно и проверить,
и порог длины — единственная механическая защита от такой отписки.

Порядок способов задан решением 18 и не переставляется: платформа →
инструменты вокруг неё → правило → справочник → и лишь затем свой скрипт.

Запуск: python -m pytest tests/test_merge_closure.py -v
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "merge-closure.py"

spec = importlib.util.spec_from_file_location("merge_closure", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["merge_closure"] = mod
spec.loader.exec_module(mod)

ДЛИННО = "Стандарт задаёт перечень из сорока видов объектов; по памяти он " \
         "воспроизводится неверно, поэтому нужен точный список." * 2
ОЧЕНЬ_ДЛИННО = ДЛИННО * 2


def единица(**over):
    u = {"что": "правила именования", "чем_закрывается": "правило",
         "почему": "Модель умеет именовать, ей нужно знать соглашение.",
         "класс_скрипта": "", "механизм": "", "объём": "абзац", "бд": False}
    u.update(over)
    return u


def файл(**over):
    d = {"раздел": "1c-metadata-objects", "единицы": [единица()], "замечания": []}
    d.update(over)
    return d


# --- годная запись ----------------------------------------------------------

def test_good_record_passes():
    assert mod.проверить(файл(), ["правила именования"]) == []


# --- перечни ----------------------------------------------------------------

def test_way_must_be_from_the_list():
    d = файл(единицы=[единица(чем_закрывается="как-нибудь")])
    notes = mod.проверить(d, ["правила именования"])
    assert any("не из перечня" in n for n in notes), notes


def test_volume_must_be_from_the_list():
    d = файл(единицы=[единица(объём="много")])
    notes = mod.проверить(d, ["правила именования"])
    assert any("объём" in n and "не из перечня" in n for n in notes), notes


def test_db_flag_must_be_boolean():
    """Пометка для решения 19 — список, а не рассуждение: только да или нет."""
    d = файл(единицы=[единица(бд="наверное")])
    notes = mod.проверить(d, ["правила именования"])
    assert any("должно быть true или false" in n for n in notes), notes


# --- соразмерность обоснования ---------------------------------------------

def test_rule_needs_no_long_justification():
    """Правило — самый дешёвый способ, объясняется одной фразой."""
    d = файл(единицы=[единица(почему="Так требует стандарт.")])
    assert mod.проверить(d, ["правила именования"]) == []


def test_script_needs_a_real_justification():
    """Короткое «нужен скрипт» нельзя оспорить, а значит нельзя и проверить."""
    d = файл(единицы=[единица(чем_закрывается="скрипт", класс_скрипта="проверяльщик",
                              почему="Нужен скрипт.")])
    notes = mod.проверить(d, ["правила именования"])
    assert any("требует обоснования не короче" in n for n in notes), notes


def test_generator_needs_the_longest_justification():
    """Генератор ошибается в сторону испорченной конфигурации.

    Планка для него выше, чем для прочих скриптов: обосновать надо, почему
    не годятся все четыре более дешёвых способа, а не один.
    """
    d = файл(единицы=[единица(чем_закрывается="скрипт", класс_скрипта="генератор",
                              почему=ДЛИННО[:100])])
    notes = mod.проверить(d, ["правила именования"])
    assert any("класса «генератор»" in n for n in notes), notes


def test_generator_with_full_justification_passes():
    d = файл(единицы=[единица(чем_закрывается="скрипт", класс_скрипта="генератор",
                              почему=ОЧЕНЬ_ДЛИННО)])
    assert mod.проверить(d, ["правила именования"]) == []


# --- поля, привязанные к способу -------------------------------------------

def test_script_must_name_its_class():
    d = файл(единицы=[единица(чем_закрывается="скрипт", класс_скрипта="", почему=ДЛИННО)])
    notes = mod.проверить(d, ["правила именования"])
    assert any("класс скрипта" in n and "не из перечня" in n for n in notes), notes


def test_class_without_script_is_reported():
    d = файл(единицы=[единица(класс_скрипта="обёртка")])
    notes = mod.проверить(d, ["правила именования"])
    assert any("класс скрипта заполнен" in n for n in notes), notes


def test_platform_mechanism_must_be_named():
    """Механизм без имени и места описания проверить нельзя.

    Это тот же запрет, что и на выдуманный номер стандарта: правдоподобная
    ссылка на «штатное средство» стоит ноль усилий.
    """
    d = файл(единицы=[единица(чем_закрывается="штатный механизм", механизм="",
                              почему=ДЛИННО)])
    notes = mod.проверить(d, ["правила именования"])
    assert any("он не назван" in n for n in notes), notes


def test_named_mechanism_passes():
    d = файл(единицы=[единица(чем_закрывается="штатный механизм",
                              механизм="webinst, руководство администратора, раздел 4.14",
                              почему=ДЛИННО)])
    assert mod.проверить(d, ["правила именования"]) == []


def test_mechanism_without_that_way_is_reported():
    d = файл(единицы=[единица(механизм="webinst")])
    notes = mod.проверить(d, ["правила именования"])
    assert any("механизм заполнен" in n for n in notes), notes


# --- полнота ----------------------------------------------------------------

def test_missing_unit_is_reported():
    notes = mod.проверить(файл(), ["правила именования", "выбор вида объекта"])
    assert any("не разобраны 1" in n for n in notes), notes


def test_alien_unit_is_reported():
    notes = mod.проверить(файл(), [])
    assert any("не из этого раздела" in n for n in notes), notes


def test_duplicate_unit_is_reported():
    d = файл(единицы=[единица(), единица()])
    notes = mod.проверить(d, ["правила именования"])
    assert any("разобрана дважды" in n for n in notes), notes


# --- отказ вместо пустоты ---------------------------------------------------

def test_refuses_without_outputs(tmp_path):
    (tmp_path / "1c-queries.json").write_text(
        json.dumps({"единицы": [{"что": "x"}]}, ensure_ascii=False), encoding="utf-8", errors="replace")
    r = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 2
    assert "out-*.json" in (r.stdout + r.stderr)


def test_unanalysed_section_is_reported(tmp_path):
    for имя in ("1c-queries", "1c-security"):
        (tmp_path / (имя + ".json")).write_text(
            json.dumps({"единицы": [{"что": "x"}]}, ensure_ascii=False), encoding="utf-8", errors="replace")
    (tmp_path / "out-1c-queries.json").write_text(
        json.dumps(файл(раздел="1c-queries",
                        единицы=[единица(что="x")]), ensure_ascii=False), encoding="utf-8", errors="replace")
    _, problems = mod.merge(tmp_path)
    assert any("1c-security не разобран" in p for p in problems), problems
