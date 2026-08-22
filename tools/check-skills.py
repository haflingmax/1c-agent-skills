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

# Поля, разрешённые спецификацией (agentskills.io/specification — шесть полей,
# а не пять; compatibility добавлен по находке Н-05/М-22 docs/reviews/2026-08-23-core-review.md:
# без него линтер строже спецификации и отвергает законный навык с этим полем).
# argument-hint сюда НЕ входит: это поле слэш-команд Claude Code, а не навыка.
SPEC_FIELDS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}

MIN_COMPAT = 1
MAX_COMPAT = 500   # agentskills.io/specification: «Must be 1-500 characters if provided»

# Обращение на «ты»/«вы» и от первого лица. Описание попадает в системную подсказку,
# и разнобой лица ломает выбор навыка. «use this» сюда сознательно не входит
# (было — находка М-24 docs/reviews/2026-08-23-core-review.md): лучший образец
# из сравнения, superpowers 6.3.0, в своём главном навыке пишет описание
# "You MUST use this before any creative work..." (skills/brainstorming/
# SKILL.md) — рабочая, рекомендуемая формулировка, которую старое правило
# отвергало бы. Настоящий признак нарушения третьего лица по официальному
# «Avoid»-примеру Anthropic — это адресация «you can»/«I can», а не сама
# фраза «use this»: их «Avoid: You can use this to process Excel files»
# ловится через «you can», «use this» как отдельный маркер лишний.
NOT_THIRD_PERSON = re.compile(
    r"\b(используй|используйте|примени|применяй|запусти|запускай|создай|укажи|вызови|"
    r"проверь|сделай|ты\s|вы\s|вам\b|тебе\b|I can|you can|I will|helps you)\b",
    re.I)

# Признак применения: описание обязано говорить не только что делает, но и когда применять.
WHEN_TO_USE = re.compile(r"применяется,?\s+когда|используется,?\s+когда|use when|when the user", re.I)

MAX_NAME = 64
MAX_DESC = 1024
MAX_BODY_LINES = 500
# 20000 было выведено из английского счёта «~4 знака на токен» (находки М-04,
# М-15, М-23 docs/reviews/2026-08-23-core-review.md), а тела навыков целиком
# кириллические. Кириллица токенизируется плотнее: живой замер локальным BPE-
# токенизатором Llama (offline-суррогат, точного офлайн-токенизатора Claude
# нет) на обоих SKILL.md репозитория дал ~3.0 знака/токен против ~5.45 у
# контрольного английского текста того же объёма — воспроизвести:
#   python -c "from tokenizers import Tokenizer; ..." (см. docs/reviews).
# Отсюда порог для «до 5 тысяч токенов» на кириллице — 5000×3 = 15000 знаков,
# а не 20000.
MAX_BODY_CHARS = 15000   # ориентир для «до 5 тысяч токенов» (кириллица, ~3 знака/токен)


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

    if "compatibility" in fm:
        compat = fm["compatibility"]
        if not (MIN_COMPAT <= len(compat) <= MAX_COMPAT):
            bad.append("compatibility длиной %d знаков — нужно %d–%d"
                        % (len(compat), MIN_COMPAT, MAX_COMPAT))

    if re.search(r"[A-Za-z_}\]]\\[A-Za-z_{]", body):
        bad.append("обратные косые в путях — нужны прямые, даже под Windows")

    if re.search(r"\$\{?(CLAUDE|KILO|CURSOR)_[A-Z_]*\}?", text):
        bad.append("привязка к переменным конкретной среды — пути должны быть относительными")

    # Документация запрещает цепочку ссылок SKILL.md → файл → файл, а не
    # глубокий путь как таковой (находка М-01 docs/reviews/2026-08-23-core-
    # review.md): счёт слэшей в самой ссылке ловит законный вложенный путь
    # references/раздел/файл.md и пропускает настоящую цепочку через один
    # слэш. Проверяем смысл документации напрямую: файл, на который ссылается
    # SKILL.md, сам не должен ссылаться дальше ни на один .md.
    for link in re.findall(r"\]\(([^)]+\.md)\)", body):
        if link.startswith(".."):
            bad.append("ссылка выше уровня навыка: %s" % link)
            continue
        target = skill_md.parent / link
        if not target.exists():
            bad.append("ссылка ведёт в никуда: %s" % link)
            continue
        deeper = re.findall(r"\]\(([^)]+\.md)\)", target.read_text(encoding="utf-8"))
        if deeper:
            bad.append("цепочка ссылок глубже одного уровня: %s → %s"
                        % (link, ", ".join(deeper)))

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
