"""Проверка навыков набора на соответствие спецификации Agent Skills.

Источник требований — официальная документация Anthropic:
https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices

Возвращает ненулевой код при любом нарушении, поэтому годится для CI.

    python tools/check-skills.py            # проверить все навыки
    python tools/check-skills.py --verbose  # показать и то, что прошло
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

# Поля, разрешённые спецификацией. argument-hint сюда НЕ входит: это поле
# слэш-команд Claude Code, а не навыка.
SPEC_FIELDS = {"name", "description", "license", "allowed-tools", "metadata"}

# Обращение на «ты»/«вы» и от первого лица. Описание попадает в системную подсказку,
# и разнобой лица ломает выбор навыка.
NOT_THIRD_PERSON = re.compile(
    r"\b(используй|используйте|примени|применяй|запусти|запускай|создай|укажи|вызови|"
    r"проверь|сделай|ты\s|вы\s|вам\b|тебе\b|I can|you can|use this|I will|helps you)\b",
    re.I)

# Признак применения: описание обязано говорить не только что делает, но и когда применять.
WHEN_TO_USE = re.compile(r"применяется,?\s+когда|используется,?\s+когда|use when|when the user", re.I)

MAX_NAME = 64
MAX_DESC = 1024
MAX_BODY_LINES = 500
MAX_BODY_CHARS = 20000   # ориентир для «до 5 тысяч токенов»


def frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return None, text
    fm = dict(re.findall(r"^([A-Za-z_-]+):\s*(.*)$", m.group(1), re.M))
    return {k: v.strip() for k, v in fm.items()}, text[m.end():]


def check(skill_md):
    """Возвращает список нарушений для одного навыка."""
    folder = skill_md.parent.name
    text = skill_md.read_text(encoding="utf-8")
    fm, body = frontmatter(text)
    bad = []
    if fm is None:
        return ["нет фронтматтера"]

    name = fm.get("name", "")
    desc = fm.get("description", "")

    if not name:
        bad.append("нет поля name")
    else:
        if len(name) > MAX_NAME:
            bad.append("name длиннее %d знаков" % MAX_NAME)
        if not re.fullmatch(r"[a-z0-9-]+", name):
            bad.append("name: разрешены только строчные латинские буквы, цифры и дефис")
        if re.search(r"claude|anthropic", name, re.I):
            bad.append("name содержит зарезервированное слово (claude/anthropic)")
        if "<" in name or ">" in name:
            bad.append("name содержит XML-теги")
        if name != folder:
            bad.append("name «%s» не совпадает с именем папки «%s»" % (name, folder))

    if not desc:
        bad.append("нет поля description")
    else:
        if len(desc) > MAX_DESC:
            bad.append("description длиннее %d знаков" % MAX_DESC)
        if "<" in desc or ">" in desc:
            bad.append("description содержит XML-теги")
        if not WHEN_TO_USE.search(desc):
            bad.append("description не говорит, КОГДА применять навык")
        m = NOT_THIRD_PERSON.search(desc)
        if m:
            bad.append("description не в третьем лице: «%s»" % m.group(0).strip())

    lines = body.count("\n")
    if lines > MAX_BODY_LINES:
        bad.append("тело %d строк, предел %d" % (lines, MAX_BODY_LINES))
    if len(body) > MAX_BODY_CHARS:
        bad.append("тело %d знаков, ориентир %d" % (len(body), MAX_BODY_CHARS))

    extra = set(fm) - SPEC_FIELDS
    if extra:
        bad.append("поля вне спецификации: %s" % ", ".join(sorted(extra)))

    if re.search(r"[A-Za-z_}\]]\\[A-Za-z_{]", body):
        bad.append("обратные косые в путях — нужны прямые, даже под Windows")

    if re.search(r"\$\{?(CLAUDE|KILO|CURSOR)_[A-Z_]*\}?", text):
        bad.append("привязка к переменным конкретной среды — пути должны быть относительными")

    for link in re.findall(r"\]\(([^)]+\.md)\)", body):
        if link.startswith("..") or link.count("/") > 1:
            bad.append("ссылка глубже одного уровня: %s" % link)
        elif not (skill_md.parent / link).exists():
            bad.append("ссылка ведёт в никуда: %s" % link)

    return bad


def main():
    verbose = "--verbose" in sys.argv
    if not SKILLS.exists():
        print("нет каталога skills/")
        return 1
    found = sorted(SKILLS.rglob("SKILL.md"))
    if not found:
        print("навыков не найдено")
        return 1

    total_bad = 0
    for skill_md in found:
        bad = check(skill_md)
        total_bad += len(bad)
        if bad:
            print("[!] %s" % skill_md.parent.name)
            for b in bad:
                print("      %s" % b)
        elif verbose:
            print("[ok] %s" % skill_md.parent.name)

    print()
    print("навыков проверено: %d, нарушений: %d" % (len(found), total_bad))
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main())
