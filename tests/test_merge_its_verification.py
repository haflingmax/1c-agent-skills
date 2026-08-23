"""Регрессия сведения сверки с ИТС (РАЗБОР-2б).

Главное, что здесь сторожится, — **опора**. На прошлых этапах она вела к файлу
референса; теперь обязана вести к документу официальной документации, и это
проверяется не глазами: номер стандарта ищется в выгруженном корпусе.

Ссылка на несуществующий стандарт — самый дешёвый способ выдать догадку
за проверенное. Правдоподобный номер стоит ноль усилий и выглядит как работа.

Запуск: python -m pytest tests/test_merge_its_verification.py -v
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "merge-its-verification.py"

spec = importlib.util.spec_from_file_location("merge_its_verification", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["merge_its_verification"] = mod
spec.loader.exec_module(mod)

IDS = {"724", "737", "542"}


def тема(**over):
    r = {"тема": "проверка прав доступа",
         "итс": "подтверждает",
         "что_говорит": "Требует ПравоДоступа вместо РольДоступна.",
         "источник": "std737 /db/v8std/content/737/hdoc"}
    r.update(over)
    return r


def пробел(**over):
    r = {"тема": "минимизация серверных вызовов",
         "о_чём": "Сколько раз за одно действие ходить на сервер.",
         "источник": "std724",
         "обязательность": "стандарт"}
    r.update(over)
    return r


def файл(**over):
    d = {"раздел": "1c-access-rights", "темы": [тема()], "пробелы": [пробел()],
         "противоречия": [], "замечания": []}
    d.update(over)
    return d


# --- опора: главная проверка этапа -----------------------------------------

def test_good_record_passes():
    assert mod.проверить(файл(), ["проверка прав доступа"], IDS) == []


def test_invented_standard_number_is_caught():
    """Ссылка на несуществующий стандарт не должна пройти.

    Правдоподобный номер стоит ноль усилий и выглядит как проверенная работа.
    Единственная защита — сверка с корпусом.
    """
    d = файл(темы=[тема(источник="std999 /db/v8std/content/999/hdoc")])
    notes = mod.проверить(d, ["проверка прав доступа"], IDS)
    assert any("нет документов 999" in n for n in notes), notes


def test_empty_source_is_caught():
    d = файл(темы=[тема(источник="")])
    notes = mod.проверить(d, ["проверка прав доступа"], IDS)
    assert any("пустой источник" in n for n in notes), notes


def test_source_without_any_reference_is_caught():
    """Опора без номера и без главы — не опора, а слова."""
    d = файл(темы=[тема(источник="так написано в документации")])
    notes = mod.проверить(d, ["проверка прав доступа"], IDS)
    assert any("нет ни номера стандарта" in n for n in notes), notes


def test_guide_chapter_counts_as_a_source():
    """Шесть разделов стоят не на стандартах, а на руководстве разработчика."""
    d = файл(темы=[тема(источник="руководство разработчика, глава 2, §2.17.5.3")])
    assert mod.проверить(d, ["проверка прав доступа"], IDS) == []


def test_gap_marked_as_standard_needs_a_standard_number():
    """Пробел, объявленный требованием стандарта, обязан назвать стандарт.

    Глава руководства описывает механизм, но не делает его обязательным —
    это разные уровни, и путать их нельзя.
    """
    d = файл(пробелы=[пробел(источник="глава 4 руководства разработчика",
                             обязательность="стандарт")])
    notes = mod.проверить(d, ["проверка прав доступа"], IDS)
    assert any("нет ни номера стандарта" in n for n in notes), notes


def test_gap_marked_as_guide_may_cite_a_chapter():
    d = файл(пробелы=[пробел(источник="глава 2 руководства разработчика",
                             обязательность="руководство")])
    assert mod.проверить(d, ["проверка прав доступа"], IDS) == []


# --- «молчит» --------------------------------------------------------------

def test_silence_must_say_what_was_searched():
    """«ИТС молчит» — утверждение, и оно требует показать, чем искали.

    Инструмент поиска прямо предупреждает, что ненайденное не равно
    отсутствующему: тема в стандартах может называться иначе.
    """
    d = файл(темы=[тема(итс="молчит", источник="")])
    notes = mod.проверить(d, ["проверка прав доступа"], IDS)
    assert any("какими словами искали" in n for n in notes), notes


def test_silence_with_search_terms_passes():
    d = файл(темы=[тема(итс="молчит",
                        источник="искал: «кэш формы», «повторное использование», «reuse»")])
    assert mod.проверить(d, ["проверка прав доступа"], IDS) == []


# --- исходы и полнота ------------------------------------------------------

def test_outcome_must_be_from_the_list():
    d = файл(темы=[тема(итс="частично")])
    notes = mod.проверить(d, ["проверка прав доступа"], IDS)
    assert any("не из перечня" in n for n in notes), notes


def test_unverified_topic_is_reported():
    notes = mod.проверить(файл(), ["проверка прав доступа", "профили групп доступа"], IDS)
    assert any("не сверены 1" in n for n in notes), notes


def test_alien_topic_is_reported():
    notes = mod.проверить(файл(), [], IDS)
    assert any("не из этого раздела" in n for n in notes), notes


def test_duplicate_topic_is_reported():
    d = файл(темы=[тема(), тема()])
    notes = mod.проверить(d, ["проверка прав доступа"], IDS)
    assert any("сверена дважды" in n for n in notes), notes


# --- противоречие нельзя оставить одной пометкой ---------------------------

def test_contradiction_must_be_described():
    """Противоречие — самая ценная находка этапа: чужой набор учит неверному.

    Пометка без описания обесценивает её: следующий этап не узнает, в чём
    именно расхождение.
    """
    d = файл(темы=[тема(итс="противоречит")], противоречия=[])
    notes = mod.проверить(d, ["проверка прав доступа"], IDS)
    assert any("не описана" in n for n in notes), notes


def test_described_contradiction_passes():
    d = файл(темы=[тема(итс="противоречит")],
             противоречия=[{"тема": "проверка прав доступа",
                            "суть": "набор советует РольДоступна, std737 требует ПравоДоступа"}])
    assert mod.проверить(d, ["проверка прав доступа"], IDS) == []


# --- отказ вместо пустоты --------------------------------------------------

def test_refuses_without_outputs(tmp_path):
    (tmp_path / "1c-queries.json").write_text(
        json.dumps({"темы": [{"тема": "x"}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 2
    assert "out-*.json" in (r.stdout + r.stderr)


@pytest.mark.skipif(not (ROOT / "_its" / "v8std-full.json").is_file(),
                    reason="_its/ под gitignore")
def test_corpus_ids_include_known_standards():
    """Проверка опоры имеет смысл, только если корпус действительно загружен."""
    ids = mod.корпус_ид()
    assert len(ids) > 1000
    assert "724" in ids and "737" in ids
