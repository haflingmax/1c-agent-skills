"""Проверка навыков набора на соответствие спецификации Agent Skills.

Источник требований — официальная документация Anthropic:
https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices

Возвращает ненулевой код при любом нарушении, поэтому годится для CI.
Предупреждения ([внимание]) в код возврата не входят — правило 11 набора:
блокировать только то, что неверно при любых обстоятельствах.

    python tools/check-skills.py            # проверить все навыки
    python tools/check-skills.py --verbose  # показать и то, что прошло
"""
import re
import sys
from pathlib import Path

# Потоки вывода переводятся в UTF-8 до первой печати. Отчёт весь на русском, а
# на Windows stdout берёт кодировку консоли (cp1251 здесь, cp866 в cmd.exe), а
# не UTF-8 — и печать падает UnicodeEncodeError на первом же символе вне этой
# кодировки, обрывая отчёт ровно там, где он начал сообщать находки. Проверено
# запуском 25.08.2026, Python 3.14, консоль cp1251: на навыке с цепочкой ссылок
# SKILL.md -> a.md -> b.md команда `env -u PYTHONIOENCODING python
# tools/check-skills.py` печатала имя навыка и падала трассировкой с кодом 1 на
# стрелке из сообщения «цепочка ссылок глубже одного уровня», а на чистом
# наборе без находок печатала кириллицу мусором. В cp866 не кодируются ещё и
# «—», «–», ««», «»» — там непечатно почти любое сообщение о нарушении или
# предупреждении, включая «compatibility длиной N знаков — нужно 1–500».
# Ветвления по sys.platform здесь намеренно нет: на Linux и macOS потоки и так
# UTF-8, а лишняя ветка — ещё один путь исполнения, который никто не проверяет.
# try/except нужен потому, что под pytest потоки подменены: у подмены может не
# быть reconfigure (AttributeError) либо она откажется перенастраивать уже
# начатый поток (ValueError), а ронять проверяльщик из-за косметики вывода
# нельзя.
for _поток in (sys.stdout, sys.stderr):
    try:
        _поток.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

# Поля, разрешённые спецификацией (agentskills.io/specification — шесть полей,
# а не пять; compatibility добавлен по находке Н-05/М-22 docs/reviews/2026-08-23-core-review.md:
# без него линтер строже спецификации и отвергает законный навык с этим полем).
# argument-hint сюда НЕ входит: это поле слэш-команд Claude Code, а не навыка.
SPEC_FIELDS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}

# M-6 финального ревью: СПЕЦИФИКАЦИЯ ШИРЕ КОНТРАКТА CODEX, и разойтись они
# могут молча. Официальный валидатор Codex (quick_validate.py из bundled-навыка
# skill-creator) знает ровно пять полей — compatibility в их число не входит.
# Проверено запуском 23.08.2026 на копии поставляемого навыка с добавленным
# полем:
#
#   quick_validate.py <копия с compatibility> ->
#       «Unexpected key(s) in SKILL.md frontmatter: compatibility.
#        Allowed properties are: allowed-tools, description, license,
#        metadata, name», код 1
#   quick_validate.py skills/developing-1c-configurations -> «Skill is valid!», код 0
#
# То есть добавивший compatibility сломает Codex, а не спецификацию, и наш
# линтер по построению этого не увидит: он сверяется со спецификацией.
# Поэтому поля, законные по спецификации, но отвергаемые Codex, дают
# ПРЕДУПРЕЖДЕНИЕ с нулевым кодом — блокировать законное по спецификации поле
# нельзя (правило 11), а молчать о том, что оно ломает вторую среду, — значит
# повторить Н-01 в профиль.
CODEX_FRONTMATTER_FIELDS = {"name", "description", "license", "allowed-tools", "metadata"}

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

# Было: MAX_BODY_CHARS = 20000, глобальный порог в знаках, подписанный как
# «ориентир для 5 тысяч токенов» на английском счёте «~4 знака/токен».
# Пересчёт под кириллицу (задача 1, находки М-04/М-15/М-23) заменил его на
# MAX_BODY_CHARS = 15000 — но порог остался ГЛОБАЛЬНЫМ числом знаков, а
# конверсия знаки→токены зависит от языка тела. На чужом английском навыке
# (superpowers 6.3.0, skills/brainstorming/SKILL.md, 15119 знаков) это
# заблокировало законное: 15119 английских знаков — это ~2750 токенов
# (вдвое меньше цели 5000), а не превышение. Ревью задачи 1 поймало это как
# Critical: новая блокировка законного недопустима (правило 11).
#
# Поэтому порог больше не задан в знаках. Оценка токенов считается по
# фактическому составу тела — доле кириллицы среди букв — и сравнивается с
# целью в 5000 токенов напрямую. Коэффициенты «знаков на токен» — из живого
# замера локальным BPE-токенизатором Llama (offline-суррогат: точного
# офлайн-токенизатора Claude в системе нет), воспроизвести:
#   from tokenizers import Tokenizer
#   tok = Tokenizer.from_file(<локальный tokenizer.json>)
#   len(text) / len(tok.encode(text).ids)
# Результат на обоих SKILL.md репозитория (кириллица) — ~3.0 знака/токен;
# на контрольном английском тексте того же объёма — ~5.45 знака/токен.
CYR_CHARS_PER_TOKEN = 3.0
LATIN_CHARS_PER_TOKEN = 5.45
BODY_TOKEN_BUDGET = 5000   # ориентир Anthropic: «до 5 тысяч токенов» на тело SKILL.md

CYRILLIC_LETTER = re.compile(r"[а-яёА-ЯЁ]")
LATIN_LETTER = re.compile(r"[A-Za-z]")


def estimate_body_tokens(body):
    """Оценивает число токенов тела по смеси кириллицы/латиницы в нём.

    Линейная интерполяция между двумя измеренными коэффициентами «знаков на
    токен» по доле кириллицы среди букв — не глобальная константа. Если в
    теле нет ни кириллицы, ни латиницы (голый код, таблицы чисел), оценка
    ненадёжна и функция возвращает None — вызывающий код обязан в этом
    случае ничего не проверять, а не подставлять произвольный коэффициент.
    """
    cyr = len(CYRILLIC_LETTER.findall(body))
    lat = len(LATIN_LETTER.findall(body))
    letters = cyr + lat
    if letters == 0:
        return None
    cyr_share = cyr / letters
    chars_per_token = (cyr_share * CYR_CHARS_PER_TOKEN
                        + (1 - cyr_share) * LATIN_CHARS_PER_TOKEN)
    return len(body) / chars_per_token


def frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return None, text
    fm = dict(re.findall(r"^([A-Za-z_-]+):\s*(.*)$", m.group(1), re.M))
    return {k: v.strip() for k, v in fm.items()}, text[m.end():]


def check(skill_md):
    """Возвращает (errors, warnings) для одного навыка.

    errors — нарушения, дающие код возврата 1 (правило 11: только то, что
    неверно при любых обстоятельствах). warnings — предупреждения с нулевым
    кодом, повод перечитать, а не запрет; сюда идёт всё, что построено на
    оценке, а не на факте о файле (см. estimate_body_tokens)."""
    folder = skill_md.parent.name
    text = skill_md.read_text(encoding="utf-8")
    fm, body = frontmatter(text)
    bad = []
    warn = []
    if fm is None:
        return ["нет фронтматтера"], []

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

    # Оценка токенов — не факт о файле, а приближение по составу символов
    # (см. комментарий у estimate_body_tokens). Превышение оценки не «неверно
    # при любых обстоятельствах» (правило 11), поэтому только предупреждение,
    # даже когда оценка велика с запасом.
    est = estimate_body_tokens(body)
    if est is not None and est > BODY_TOKEN_BUDGET:
        warn.append("тело ~%d токенов по оценке (%d знаков), ориентир %d — "
                     "оценка приблизительна, не блокирует"
                     % (round(est), len(body), BODY_TOKEN_BUDGET))

    extra = set(fm) - SPEC_FIELDS
    if extra:
        bad.append("поля вне спецификации: %s" % ", ".join(sorted(extra)))

    # M-6: законно по спецификации, но отвергается валидатором Codex.
    codex_extra = (set(fm) & SPEC_FIELDS) - CODEX_FRONTMATTER_FIELDS
    if codex_extra:
        warn.append(
            "%s — законное поле спецификации, но официальный валидатор Codex "
            "его отвергает («Unexpected key(s) in SKILL.md frontmatter», "
            "проверено запуском): в Codex навык перестанет ставиться. "
            "Не блокирует — решай по тому, нужен ли Codex"
            % ", ".join(sorted(codex_extra)))

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

    return bad, warn


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
    total_warn = 0
    for skill_md in found:
        bad, warn = check(skill_md)
        total_bad += len(bad)
        total_warn += len(warn)
        if bad or warn:
            print("[!] %s" % skill_md.parent.name)
            for b in bad:
                print("      %s" % b)
            for w in warn:
                print("      [внимание] %s" % w)
        elif verbose:
            print("[ok] %s" % skill_md.parent.name)

    print()
    print("навыков проверено: %d, нарушений: %d, предупреждений: %d"
          % (len(found), total_bad, total_warn))
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main())
