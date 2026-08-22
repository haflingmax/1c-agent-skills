"""Проверка того, что утверждения о необратимости несут источник."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("check_sources", ROOT / "tools" / "check-sources.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["check_sources"] = mod
spec.loader.exec_module(mod)


def test_claim_without_source_is_caught(tmp_path):
    f = tmp_path / "SKILL.md"
    f.write_text("## Что здесь необратимо\n\nНеобратимо изменение структуры.\n",
                 encoding="utf-8")
    assert mod.check_file(f), "утверждение без источника должно ловиться"


def test_claim_with_source_passes(tmp_path):
    f = tmp_path / "SKILL.md"
    f.write_text("## Что здесь необратимо\n\nНеобратимо изменение структуры "
                 "(стандарт «Организация хранения данных»).\n", encoding="utf-8")
    assert not mod.check_file(f)


def test_file_without_section_is_ignored(tmp_path):
    f = tmp_path / "SKILL.md"
    f.write_text("## Другое\n\nПросто текст.\n", encoding="utf-8")
    assert not mod.check_file(f)


# --- Класс 2: висячая ссылка на раздел другого навыка по имени -------------
#
# Задача 3 переименовала раздел ядра «Решения, которые принимаются до кода» в
# «Что выяснить до первой правки». В skills/1c-build-and-db/SKILL.md осталась
# ссылка на старое имя, и check-skills.py её не поймал: он проверяет только
# markdown-ссылки вида [текст](файл.md), а не упоминания разделов по названию
# в кавычках-ёлочках.


def test_dangling_section_reference_is_caught(tmp_path):
    ref = tmp_path / "SKILL.md"
    ref.write_text(
        "Это решение уровня плана — см. раздел «Решения, которые принимаются "
        "до кода» в ядре.\n", encoding="utf-8")
    core = tmp_path / "CORE.md"
    core.write_text("## Что выяснить до первой правки\n\nТекст.\n", encoding="utf-8")
    bad = mod.find_dangling_refs([ref, core])
    assert bad, "ссылка на переименованный раздел должна ловиться как висячая"


def test_section_reference_with_existing_heading_passes(tmp_path):
    ref = tmp_path / "SKILL.md"
    ref.write_text(
        "Это решение уровня плана — см. раздел «Что выяснить до первой "
        "правки» в ядре.\n", encoding="utf-8")
    core = tmp_path / "CORE.md"
    core.write_text("## Что выяснить до первой правки\n\nТекст.\n", encoding="utf-8")
    bad = mod.find_dangling_refs([ref, core])
    assert not bad, "ссылка на существующий раздел ловиться не должна"


def test_task3_renamed_heading_case_reproduced(tmp_path):
    """Повтор реального случая: временно возвращаем старое имя раздела в
    отдельном временном файле и проверяем его против фактического набора
    навыков — старого имени там больше нет, ссылка обязана пойматься."""
    old_name_ref = tmp_path / "SKILL.md"
    old_name_ref.write_text(
        "Это решение уровня плана — см. раздел «Решения, которые "
        "принимаются до кода» в ядре.\n", encoding="utf-8")
    real_skill_files = sorted((ROOT / "skills").rglob("*.md"))
    bad = mod.find_dangling_refs(real_skill_files + [old_name_ref])
    assert bad, "старого имени раздела в наборе навыков больше нет — ссылка должна ловиться"


def test_no_dangling_section_refs_in_current_skills():
    """Регресс: в текущем наборе навыков висячих ссылок на разделы быть не должно."""
    real_skill_files = sorted((ROOT / "skills").rglob("*.md"))
    bad = mod.find_dangling_refs(real_skill_files)
    assert not bad, "в наборе навыков не должно быть висячих ссылок: %r" % (bad,)
