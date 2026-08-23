"""Регрессия сведения читающего слоя описи референсов (РАЗБОР-1а).

Читающий слой — суждение агентов-читателей, воспроизвести его перезапуском
нельзя. Поэтому он проверяется на входе, и здесь проверяется сама проверка:
она обязана ловить незаполненное, выдуманный раздел, цитату без опоры,
молчание о разнице версий и просочившийся вердикт.

Запуск: python -m pytest tests/test_merge_reference_reading.py -v
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "merge-reference-reading.py"

spec = importlib.util.spec_from_file_location("merge_reference_reading", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["merge_reference_reading"] = mod
spec.loader.exec_module(mod)


def make_units(tmp_path, paired=False):
    """Две единицы: одна непарная, одна парная — и живой файл под цитату."""
    f = tmp_path / "cc-1c-skills" / ".claude" / "skills" / "cf-edit"
    f.mkdir(parents=True)
    (f / "SKILL.md").write_text("тело", encoding="utf-8")
    return {"cf-edit": [{}, {}] if paired else [{}]}


def good(name="cf-edit", **over):
    rec = {
        "единица": name,
        "суть": "Правит свойства конфигурации точечно.",
        "входы_выходы": "XML-выгрузка конфигурации, ключ -Operation.",
        "раздел": "1c-build-and-db",
        "почему_раздел": "работает с выгрузкой конфигурации.",
        "опора": "платформа",
        "скрипты": "PowerShell-обёртка над конфигуратором.",
        "разница_версий": "",
        "цитата": "«точечное редактирование» — cc-1c-skills/.claude/skills/cf-edit/SKILL.md:12",
    }
    rec.update(over)
    return rec


# --- годная запись замечаний не вызывает ----------------------------------

def test_good_record_has_no_notes(tmp_path):
    units = make_units(tmp_path)
    assert mod.check_record(good(), units, tmp_path) == []


# --- обязательные поля -----------------------------------------------------

def test_missing_field_is_caught(tmp_path):
    units = make_units(tmp_path)
    rec = good()
    del rec["почему_раздел"]
    notes = mod.check_record(rec, units, tmp_path)
    assert any("нет полей" in n and "почему_раздел" in n for n in notes), notes


def test_empty_essence_is_caught(tmp_path):
    units = make_units(tmp_path)
    notes = mod.check_record(good(суть="   "), units, tmp_path)
    assert any("пустая суть" in n for n in notes), notes


# --- раздел берётся из списка, а не из головы ------------------------------

def test_invented_section_is_caught(tmp_path):
    """Раздел не из шестнадцати — выдумка, даже если звучит правдоподобно."""
    units = make_units(tmp_path)
    notes = mod.check_record(good(раздел="1c-command-line"), units, tmp_path)
    assert any("не из списка" in n for n in notes), notes


def test_outside_layout_is_a_legal_answer(tmp_path):
    """«Вне раскладки» — законный ответ, а не поражение читателя.

    Наша раскладка сверена с системой стандартов 1С. То, что в неё не легло,
    само по себе находка: чужой набор покрывает область, которой у нас нет.
    """
    units = make_units(tmp_path)
    assert mod.check_record(good(раздел="вне раскладки"), units, tmp_path) == []


# --- опора: без цитаты утверждение не на чем держится ----------------------

def test_missing_citation_is_caught(tmp_path):
    units = make_units(tmp_path)
    notes = mod.check_record(good(цитата=""), units, tmp_path)
    assert any("нет цитаты" in n for n in notes), notes


def test_citation_accepts_both_shapes(tmp_path):
    """Цитата приходит строкой или объектом — годны обе.

    Задание читателям допускало оба прочтения: «выдержка и путь:строка»
    можно понять и как одну строку, и как объект с полями. Пять читателей
    из восьми поняли первым способом, трое — вторым. Двусмысленность
    в задании не повод браковать честную работу.
    """
    units = make_units(tmp_path)
    as_dict = {"текст": "точечное редактирование",
               "путь": "cc-1c-skills/.claude/skills/cf-edit/SKILL.md:12"}
    assert mod.check_record(good(цитата=as_dict), units, tmp_path) == []


def test_citation_shape_does_not_hide_a_dead_path(tmp_path):
    """Объектная форма не должна прятать несуществующий путь."""
    units = make_units(tmp_path)
    notes = mod.check_record(
        good(цитата={"текст": "нечто",
                     "путь": "cc-1c-skills/.claude/skills/призрак/SKILL.md:3"}),
        units, tmp_path)
    assert any("не ведёт к файлу" in n for n in notes), notes


def test_citation_pointing_nowhere_is_caught(tmp_path):
    """Путь из цитаты обязан вести к живому файлу.

    Ровно так этот проект уже обжигался: оглавление, собранное без чтения,
    сослалось на разделы, которых нет.
    """
    units = make_units(tmp_path)
    notes = mod.check_record(
        good(цитата="«нечто» — cc-1c-skills/.claude/skills/призрак/SKILL.md:3"),
        units, tmp_path)
    assert any("не ведёт к файлу" in n for n in notes), notes


def test_citation_may_point_at_a_script(tmp_path):
    """Опорой вправе быть скрипт навыка, а не только markdown.

    Читатель по form-remove сослался на remove-form.py — и первая редакция
    правила забраковала его за то, что путь не оканчивается на .md.
    """
    units = make_units(tmp_path)
    scripts = tmp_path / "cc-1c-skills" / ".claude" / "skills" / "cf-edit" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "remove-form.py").write_text("# код", encoding="utf-8")
    rec = good(цитата="[ERROR] форма используется. | "
                      "cc-1c-skills/.claude/skills/cf-edit/scripts/remove-form.py:256")
    assert mod.check_record(rec, units, tmp_path) == []


def test_citation_survives_a_filename_mentioned_inside_the_quote(tmp_path):
    """Цитируемый текст сам упоминает соседние файлы — источник в конце.

    «См. [regress.md](regress.md) … — путь/SKILL.md:626»: первая редакция
    хватала regress.md и браковала честную цитату. Годится, если хоть один
    из упомянутых путей ведёт к живому файлу.
    """
    units = make_units(tmp_path)
    rec = good(цитата="switch to the `test` mode. See [regress.md](regress.md) for "
                      "discipline — cc-1c-skills/.claude/skills/cf-edit/SKILL.md:626")
    assert mod.check_record(rec, units, tmp_path) == []


# --- разница версий: молчание о ней недопустимо ----------------------------

def test_paired_unit_must_state_the_difference(tmp_path):
    units = make_units(tmp_path, paired=True)
    notes = mod.check_record(good(), units, tmp_path)
    assert any("разница версий не названа" in n for n in notes), notes


def test_unpaired_unit_must_not_invent_a_difference(tmp_path):
    units = make_units(tmp_path)
    notes = mod.check_record(good(разница_версий="вторая версия короче"), units, tmp_path)
    assert any("непарная" in n for n in notes), notes


# --- вердикт в опись не просачивается --------------------------------------

@pytest.mark.parametrize("field,text", [
    ("суть", "Делает X. Переносить стоит целиком."),
    ("почему_раздел", "по смыслу; брать не нужно."),
    ("входы_выходы", "XML-выгрузка; полезно для нас."),
])
def test_verdict_words_are_caught(tmp_path, field, text):
    """Опись описывает, а не советует.

    Читатель, который заодно оценивает, подгоняет описание под свою оценку:
    отвергнутое описывается тусклее. Владелец просил решать попунктно
    на следующем этапе — значит опись обязана прийти нейтральной.
    """
    units = make_units(tmp_path)
    notes = mod.check_record(good(**{field: text}), units, tmp_path)
    assert any("вердикт" in n for n in notes), notes


def test_neutral_wording_survives(tmp_path):
    """Ложных срабатываний на нейтральном тексте быть не должно."""
    units = make_units(tmp_path)
    rec = good(суть="Собирает отчёт СКД из схемы и настроек компоновки.")
    assert mod.check_record(rec, units, tmp_path) == []


# Живые фразы из выводов читателей, на которых первая редакция правила дала
# шесть ложных срабатываний из шести. «Перенос» в 1С — доменное слово:
# перенос вставок расширения, перенос данных, перенос строки.
DOMAIN_WORDING = [
    "Mode B — проверка переноса: ищет блоки #Вставка/#КонецВставки.",
    "Выход — текстовый отчёт по статусу переноса вставок.",
    "При отсутствии -ConfigPath пробует брать configSrc базы.",
    "Не переносит пользовательские данные: voiceprints, .env, память проектов.",
    "Текст запроса требуется писать одной строкой без переносов.",
    "XDTO-пакет и XSD, переносимые в расширение конфигурации-приёмника.",
    "Конструкции, которые модель XDTO переносит приближённо: вложенные xs:choice.",
]


@pytest.mark.parametrize("text", DOMAIN_WORDING)
def test_domain_wording_is_not_a_verdict(tmp_path, text):
    """Доменный язык 1С не должен приниматься за совет.

    Блокировка законной работы — самый дорогой класс ошибки в этом наборе,
    и здесь он был заведён собственным сторожем: правило искало корень слова
    вместо конструкции совета.
    """
    units = make_units(tmp_path)
    assert mod.check_record(good(суть=text), units, tmp_path) == [], text


# --- отказ вместо пустого файла -------------------------------------------

def test_refuses_without_reader_output(tmp_path):
    """Нет ни одного out-*.json — понятное сообщение и код 2."""
    reg = tmp_path / "registry.json"
    reg.write_text(json.dumps({"навыки": []}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path), "--registry", str(reg),
         "--ref", str(tmp_path), "--out", str(tmp_path / "o.json")],
        capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "out-*.json" in (r.stdout + r.stderr)
    assert not (tmp_path / "o.json").exists(), "пустой файл записан вопреки отказу"


def test_uncovered_unit_is_reported(tmp_path):
    """Единица без описания обязана всплыть, а не потеряться молча."""
    units = {"cf-edit": [{}], "db-run": [{}]}
    (tmp_path / "out-1.json").write_text("[]", encoding="utf-8")
    reg = tmp_path / "registry.json"
    reg.write_text(json.dumps({"навыки": [
        {"набор": "cc", "имя": "cf-edit", "пара": None},
        {"набор": "cc", "имя": "db-run", "пара": None},
    ]}, ensure_ascii=False), encoding="utf-8")
    _, problems = mod.merge(tmp_path, reg, tmp_path)
    assert any("не описаны 2" in p for p in problems), problems


def test_duplicate_unit_is_reported(tmp_path):
    """Одна единица в двух кусках — сговор или ошибка нарезки, но не норма."""
    reg = tmp_path / "registry.json"
    reg.write_text(json.dumps({"навыки": [
        {"набор": "cc", "имя": "cf-edit", "пара": None}]}, ensure_ascii=False),
        encoding="utf-8")
    make_units(tmp_path)
    for n in (1, 2):
        (tmp_path / ("out-%d.json" % n)).write_text(
            json.dumps([good()], ensure_ascii=False), encoding="utf-8")
    _, problems = mod.merge(tmp_path, reg, tmp_path)
    assert any("описана дважды" in p for p in problems), problems
