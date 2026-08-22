"""Проверка check-skills.py: язык-зависимая оценка размера тела.

Регресс на находку финального ревью задачи 1 (Critical, не одобрено с
первого захода): MAX_BODY_CHARS = 15000, пересчитанный под кириллицу
(М-04/М-15/М-23), был глобальным порогом в знаках и блокировал легальный
английский навык — на superpowers 6.3.0, skills/brainstorming/SKILL.md
(15119 знаков) давал «тело 15119 знаков, ориентир 15000» как ошибку, хотя
это лишь ~2750 токенов, вдвое меньше цели 5000. Починка: оценка токенов
считается по фактическому составу тела (доля кириллицы среди букв), а не
по глобальной константе, и живёт в канале предупреждений с нулевым кодом
возврата — правило 11 набора запрещает блокировать то, что не является
неверным при любых обстоятельствах, а оценка токенов таковым не является.

Запуск: python -m pytest tests/test_check_skills.py -v
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("check_skills", ROOT / "tools" / "check-skills.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["check_skills"] = mod
spec.loader.exec_module(mod)


def _write_skill(tmp_path, folder, name, description, body_text):
    d = tmp_path / folder
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: %s\ndescription: %s\n---\n\n%s" % (name, description, body_text),
        encoding="utf-8")
    return d / "SKILL.md"


# --- Случай рецензента: чужой английский навык не должен браковаться -------
#
# Синтетический текст, а не файл конкретного плагина: тест не должен зависеть
# от того, установлен ли superpowers в системе, где он запускается. Длина и
# состав (почти сплошь латиница, много повторов) подобраны так, чтобы
# воспроизвести именно тот класс, что поймал рецензент — «длинное английское
# тело», а не точное число 15119.

ENGLISH_PARAGRAPH = (
    "Use this skill when starting any new creative work, before writing code, "
    "before designing a feature, and before committing to an approach. It "
    "explores user intent, generates several genuinely different directions, "
    "and helps decide between them with real tradeoffs stated plainly. "
) * 90


def test_foreign_english_skill_body_size_is_not_an_error(tmp_path):
    """Английское тело длиной за старый порог 15000 не должно попадать в
    errors по размеру — старый глобальный порог в знаках это делал."""
    assert len(ENGLISH_PARAGRAPH) > 15000, "образец короче старого порога — тест ничего не проверяет"
    skill_md = _write_skill(
        tmp_path, "foreign-english-skill", "foreign-english-skill",
        "Use when creating new work. Explores user intent before implementation.",
        ENGLISH_PARAGRAPH)
    errors, warnings = mod.check(skill_md)
    size_errors = [e for e in errors if "знаков" in e or "токен" in e]
    assert not size_errors, "английское тело не должно ловиться по размеру как ошибка: %r" % size_errors


def test_real_superpowers_brainstorming_not_blocked_by_size():
    """Тот же случай на настоящем файле рецензента, если он доступен в
    системе — пропускается, если плагин не установлен (переносимость теста)."""
    real = Path(
        "C:/Users/ashil/.claude/plugins/cache/claude-plugins-official/"
        "superpowers/6.3.0/skills/brainstorming/SKILL.md")
    if not real.exists():
        pytest.skip("superpowers 6.3.0 не установлен в этой системе")
    errors, warnings = mod.check(real)
    size_errors = [e for e in errors if "знаков" in e or "токен" in e]
    assert not size_errors, "found: %r" % size_errors


# --- Обратная сторона: русское тело, реально превышающее бюджет ------------


def test_oversized_russian_body_is_still_flagged_as_warning(tmp_path):
    """Кириллическое тело, реально превышающее 5000 токенов по оценке,
    обязано ловиться — но предупреждением с нулевым кодом, а не ошибкой."""
    russian_body = (
        "Это предложение на русском языке повторяется много раз для проверки "
        "оценки размера тела навыка. "
    ) * 250
    skill_md = _write_skill(
        tmp_path, "big-ru-skill", "big-ru-skill",
        "Тестовый навык. Применяется, когда нужно проверить оценку размера.",
        russian_body)
    errors, warnings = mod.check(skill_md)
    size_errors = [e for e in errors if "знаков" in e or "токен" in e]
    size_warnings = [w for w in warnings if "токен" in w]
    assert not size_errors, "оценка токенов не должна блокировать (правило 11): %r" % size_errors
    assert size_warnings, "реально большое русское тело должно попасть хотя бы в предупреждения"


def test_body_within_budget_produces_no_size_warning(tmp_path):
    """Тело в пределах оценки бюджета не должно давать даже предупреждения —
    иначе проверка станет шумной и её начнут игнорировать."""
    skill_md = _write_skill(
        tmp_path, "small-ru-skill", "small-ru-skill",
        "Тестовый навык. Применяется, когда тело короткое.",
        "Короткое тело без претензий на объём.")
    errors, warnings = mod.check(skill_md)
    assert not [w for w in warnings if "токен" in w]


def test_real_repo_skills_have_no_size_warnings():
    """Регресс: оба реальных навыка репозитория укладываются в оценку
    бюджета без единого предупреждения по размеру."""
    for skill_md in sorted((ROOT / "skills").rglob("SKILL.md")):
        errors, warnings = mod.check(skill_md)
        size_warnings = [w for w in warnings if "токен" in w]
        assert not size_warnings, "%s: %r" % (skill_md, size_warnings)
