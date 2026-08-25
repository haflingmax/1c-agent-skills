"""Собирает cli-keys.json целиком из приложения 7 руководства администратора.

Заменяет tools/derive-glued.py, который умел только проставлять признак
`glued` в уже существующем каталоге. Этот скрипт строит каталог с нуля:
имя ключа, аргумент, список режимов, полный список опций, признак `glued`.

Источник — _its/cmdline/its-pril7-full.json (выгрузка приложения 7
руководства администратора 8.3.27). Каталог _its/ под gitignore и есть не
на каждой машине — при его отсутствии скрипт не падает молча и не пишет
пустой файл, а сообщает и завершается с кодом 2.

Как устроен источник (проверено чтением, не предположением):

- 7.3.x «Общие команды запуска» и 7.4.x «Команды пакетного режима запуска
  конфигуратора» (включая подразделы вида 7.4.15.1) документируют ключи
  построчно: имя ключа (иногда сразу с приклеенным или отделённым пробелом
  аргументом и опциями в квадратных скобках) начинает абзац, следующий
  абзац — свободное описание. Опции берутся из первого абзаца (синопсиса),
  а не из описания: там они по-настоящему полны, без обрезки.
- 7.6 «OLE-Automation» устроен так же.
- 7.2.3 «Запуск в режиме создания информационной базы» ключей построчно не
  документирует: там один синтаксический шаблон
  `1cv8 CREATEINFOBASE <строка соединения> [/AddToList ...] ... [/DumpResult ...]`,
  перечисляющий, какие ключи допустимы в этом режиме. Часть из них (/Out,
  /L, /VL, /O) уже документирована как общая в 7.3.x — общий режим шире и
  побеждает. Часть — только здесь (/AddToList, /UseTemplate). А /DumpResult
  документирован ещё и в 7.4.17 как ключ DESIGNER — вот почему у него два
  режима, а не один (Н-03 из ревью).
- 7.5, 7.7, 7.8, 7.9 не документируют новых `/Ключ`-параметров построчно:
  7.5 — только проза про пакетный режим клиента, 7.7 — параметры строки
  соединения (не начинаются с "/"), 7.8/7.9 — свой синтаксис (веб-клиент,
  мобильная версия), не совпадающий с интерфейсом 1cv8.exe. check-1c-cli.py
  разбирает только аргументы, начинающиеся с "/", поэтому эти разделы вне
  охвата — как и в прежнем каталоге.

    python tools/build-cli-keys.py

Печатает сверку: сколько ключей, сколько с несколькими режимами, сколько
опций всего. Код возврата 0 — каталог собран, записан и принят проверкой
манифестов; 2 — источника нет; 3 — записанное отвергнуто tools/check-manifests.py.

Правило набора (находка C-1 финального ревью): любой инструмент, который
пишет в skills/, обязан заканчиваться прогоном tools/check-manifests.py и
падать при ненулевом коде. Причина у C-1 была не в одном скрипте, а в том,
что записанное в skills/ никто не перечитывал.

Печать переводится в UTF-8 сразу после импортов: на Windows stdout процесса
отдан кодировке консоли (cp1251), и первая же кириллическая строка чужого
вывода роняет print с UnicodeEncodeError — проверено 25.08.2026 (Python 3.14)
прогоном `env -u PYTHONIOENCODING python tools/build-cli-keys.py`: каталог был
записан, а отчёт о сверке потерян и код возврата 1 вместо 0.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

# Кодировка печати — UTF-8, независимо от кодировки консоли (см. шапку).
# Без ветвления по sys.platform: на Linux и macOS потоки и так UTF-8, а лишняя
# ветка — лишний путь исполнения, который никто не прогоняет. try/except
# обязателен: под pytest потоки подменены, у подмены может не быть reconfigure
# или он бросит ValueError — ронять сборку каталога из-за косметики печати
# нельзя.
for _поток in (sys.stdout, sys.stderr):
    try:
        _поток.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_its" / "cmdline" / "its-pril7-full.json"
DST = ROOT / "skills" / "1c-build-and-db" / "scripts" / "cli-keys.json"
CHECK_MANIFESTS = ROOT / "tools" / "check-manifests.py"

# Варианты тире, которыми в источнике иногда записан дефис перед опцией:
# – (U+2013, короткое тире), ‑ (U+2011, неразрывный дефис), − (U+2212, знак
# минуса). Без нормализации перед разбором строка "[–update]" не опознаётся
# как опция "-update" — это и есть половина потери 30 опций (Н-09).
DASH_VARIANTS = re.compile("[\u2013\u2011\u2212]")

SECTION_RE = re.compile(r"^(7(?:\.\d+)+)\.\s+\S")
KEY_RE = re.compile(r"^/([A-Za-z@][A-Za-z0-9_]*)")
OPT_RE = re.compile(r"-([A-Za-z][A-Za-z0-9]*)")
# Признак слитности: значение приклеено к имени без пробела — регистрирует
# первый непробельный, неалфавитный символ сразу после имени ключа.
# Тот же приём, что был в tools/derive-glued.py — он проверен запусками
# и подтверждён тестом test_glued_flag_is_present_and_small (ровно 12).
GLUED_RE = re.compile(r"^(/[A-Za-z][A-Za-z0-9_]*)(.?)")

# Топ-уровень раздела -> режим построчных определений. None — общий режим:
# ключ не ограничен, побеждает при слиянии (см. merge_modes).
SECTION_MODE = {
    "7.3": None,
    "7.4": "DESIGNER",
    "7.6": "OLE",
}

# "UsePrivilegedMode" в разделе 7.3.1 записан без ведущего "/", но по смыслу
# описания («запуск клиентского приложения в привилегированном режиме») —
# это ключ режима ENTERPRISE, а не общая команда подключения. Так же он был
# размечен и в прежнем каталоге, и это подтверждено эксплуатационно —
# тестом test_alien_mode_key_inside_designer_is_only_a_note и доказательством
# docs/evidence/2026-08-22-blocking-rules.md («ключ-чужого-режима»).
BARE_KEY_MODES = {"UsePrivilegedMode": "ENTERPRISE"}

MODE_ORDER = ["CREATEINFOBASE", "DESIGNER", "ENTERPRISE", "OLE"]

# M-4. У четырёх ключей поле arg было пустым, хотя источник аргумент
# документирует. Два из них (/UseTemplate, /AddToList) чинятся данными:
# их аргумент стоит в синопсисе шаблона 7.2.3, и parse_createinfobase_template()
# теперь его оттуда берёт, а не выбрасывает.
#
# Два оставшихся достать надёжно НЕ выходит, и это записано здесь поимённо,
# а не обойдено молчанием. В разделах 7.3.1 и 7.3.2 их синопсис — голое имя
# ключа без единой угловой скобки; аргумент описан только прозой следующего
# абзаца. Проза — не синопсисная форма: превратить «Позволяет задать строку
# соединения с информационной базой целиком» в значение поля arg значит
# ВЫДУМАТЬ форму, которой в источнике нет. В наборе, где блокировать
# разрешено только доказанное, это хуже, чем честно назвать пробел.
#
# Поэтому такие ключи получают отдельное поле arg_прозой — цитату источника.
# На разбор командной строки оно не влияет: absorbs_glued_tail() смотрит
# только на arg и glued, и поведение проверяльщика для этих ключей остаётся
# прежним (проверено: /IBConnectionString "File=…" — замечаний нет, код 0).
ARG_ONLY_IN_PROSE = {
    "/IBConnectionString": (
        "7.3.1: «Позволяет задать строку соединения с информационной базой "
        "целиком в том виде, в котором ее возвращает функция "
        "СтрокаСоединенияИнформационнойБазы()». Синопсис — голое имя ключа, "
        "угловых скобок в источнике нет"),
    "/AccessToken": (
        "7.3.2: «Позволяет указать JWT для выполнения аутентификации "
        "пользователя». Синопсис — голое имя ключа, угловых скобок в "
        "источнике нет"),
}

TEMPLATES = [
    "1cv8 CREATEINFOBASE <строка соединения> [/AddToList [<имя ИБ>]] "
    "[/UseTemplate <имя файла шаблона>] [/Out <имя файла>] [/L<код языка>] "
    "[/VL<код локализации>] [/O<скорость соединения>] [/DumpResult <имя файла>]",
    "1cv8 DESIGNER /IBName \"My db\" /DumpIB c:\\temp\\dump.dt",
    "1cv8 DESIGNER [<команды >]",
    "1cv8 ENTERPRISE [<параметры запуска>]",
]

MODES_LIST = [
    "DESIGNER", "ENTERPRISE", "CREATEINFOBASE", "общий", "OLE",
    "строка соединения", "веб-клиент", "мобильная версия",
]


def fail(msg):
    print(msg)
    raise SystemExit(2)


def verify_manifests():
    """Прогоняет tools/check-manifests.py; ненулевой код — падаем.

    Скрипт пишет в skills/, а значит подчиняется правилу C-1. Вызывается
    отдельным процессом, а не импортом: проверяем ровно тот инструмент,
    который потом позовёт человек, и ровно его код возврата.
    """
    proc = subprocess.run(
        [sys.executable, str(CHECK_MANIFESTS)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    print(out.strip())
    if proc.returncode != 0:
        print(
            "[ошибка] записанный каталог отвергнут tools/check-manifests.py "
            "(код %d). Правило: инструмент, который пишет в skills/, "
            "заканчивается этой проверкой." % proc.returncode
        )
        raise SystemExit(3)


def load_source_text():
    if not SRC.exists():
        fail(
            "[ошибка] источник недоступен: %s не найден.\n"
            "Каталог _its/ под gitignore — выгрузка ИТС есть не на каждой "
            "машине. Собирать каталог не из чего: скрипт останавливается, "
            "а не пишет пустой cli-keys.json." % SRC
        )
    try:
        data = json.loads(SRC.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        fail("[ошибка] источник %s повреждён или нечитаем: %s" % (SRC, e))
    text = data.get("text") or ""
    if not text:
        fail("[ошибка] источник %s не содержит поля text — выгрузка пустая" % SRC)
    return text


def make_blocks(text):
    """Абзацы: строки без пустых строк между ними склеиваются пробелом."""
    out, cur = [], []
    for line in text.split("\n"):
        if line.strip():
            cur.append(line.strip())
        elif cur:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out


def section_top(section):
    parts = section.split(".")
    return parts[0] + "." + parts[1]


def find_glued(blocks):
    found = set()
    for b in blocks:
        m = GLUED_RE.match(b)
        if m and m.group(2) == "<":
            found.add(m.group(1))
    return found


def extract_opts(syntax):
    normalized = DASH_VARIANTS.sub("-", syntax)
    seen = []
    for m in OPT_RE.finditer(normalized):
        opt = "-" + m.group(1)
        if opt not in seen:
            seen.append(opt)
    return seen


def parse_table_style(blocks):
    """Ключи, документированные построчно в 7.3.x, 7.4.x, 7.6.

    Возвращает {имя: [(раздел, режим_или_None, синопсис), ...]}.
    """
    entries = {}
    section = None
    for b in blocks:
        m = SECTION_RE.match(b)
        if m:
            section = m.group(1)
            continue
        if section is None:
            continue
        top = section_top(section)
        if top not in SECTION_MODE:
            continue

        key_match = KEY_RE.match(b)
        if key_match:
            name = "/" + key_match.group(1)
            syntax = b[key_match.end():]
        elif top == "7.3" and b.strip() in BARE_KEY_MODES:
            name = "/" + b.strip()
            syntax = ""
        else:
            continue

        mode_tag = SECTION_MODE[top]
        if name[1:] in BARE_KEY_MODES:
            mode_tag = BARE_KEY_MODES[name[1:]]
        entries.setdefault(name, []).append((section, mode_tag, syntax))
    return entries


def bracket_groups(template):
    """Содержимое квадратных групп верхнего уровня, со счётчиком вложенности.

    «[/AddToList [<имя ИБ>]] [/Out <имя файла>]» даёт
    ['/AddToList [<имя ИБ>]', '/Out <имя файла>'].
    """
    out = []
    depth = 0
    start = None
    for i, ch in enumerate(template):
        if ch == "[":
            if depth == 0:
                start = i + 1
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0 and start is not None:
                out.append(template[start:i])
                start = None
            elif depth < 0:
                depth = 0
    return out


def parse_createinfobase_template(text):
    """7.2.3 не документирует ключи построчно — только шаблон синтаксиса.

    Каждый /Ключ, упомянутый в шаблоне, допустим и в режиме CREATEINFOBASE.
    Возвращает [(имя, аргумент), ...] и сам шаблон.

    M-4: раньше отсюда брались только имена, и аргумент, стоящий в шаблоне
    прямо за ключом («[/UseTemplate <имя файла шаблона>]»), выбрасывался —
    у /UseTemplate и /AddToList поле arg оставалось пустым, и
    absorbs_glued_tail() относил их к тому же классу, что /NoProxy
    («аргумента нет вовсе»).

    M-5: раньше, если регулярка не находила шаблон, функция МОЛЧА брала
    TEMPLATES[0] — зашитую копию. Сегодня результат совпал бы, но изменение
    формата выгрузки оказалось бы замаскировано вместо того, чтобы быть
    названным. Теперь она падает так же, как load_source_text(): в наборе,
    который лечится от «заявление шире доказательства», тихий откат — тот же
    дефект в профиль.
    """
    m = re.search(r"CREATEINFOBASE\s+<строка соединения>.*?/DumpResult[^\]]*\]", text)
    if not m:
        fail(
            "[ошибка] в источнике %s не найден шаблон 7.2.3 "
            "«CREATEINFOBASE <строка соединения> … /DumpResult …».\n"
            "Раньше здесь молча подставлялась зашитая копия TEMPLATES[0], и "
            "изменение формата выгрузки маскировалось вместо того, чтобы быть "
            "названным. Собирать каталог не из чего: скрипт останавливается."
            % SRC
        )
    template = m.group(0)

    # Аргумент ключа берётся из ЕГО СОБСТВЕННОЙ квадратной группы, а не
    # «до следующего ключа»: второе цепляет закрывающие скобки соседей и
    # портит уже верные значения (у /L получалось «<код языка>] [» вместо
    # «<код языка>»). Группы разбираются со счётчиком вложенности —
    # «[/AddToList [<имя ИБ>]]» вложена, и обрывать её по первому «]» нельзя.
    entries = []
    seen = set()
    for group in bracket_groups(template):
        km = re.match(r"\s*/([A-Za-z@][A-Za-z0-9_]*)", group)
        if not km:
            continue
        name = "/" + km.group(1)
        if name in seen:
            continue
        seen.add(name)
        entries.append((name, group[km.end():].strip()))
    return entries, template


def merge_modes(mode_tags):
    if None in mode_tags:
        return []
    return [m for m in MODE_ORDER if m in mode_tags]


def build_catalog():
    text = load_source_text()
    blocks = make_blocks(text)

    glued = find_glued(blocks)
    table_entries = parse_table_style(blocks)
    createinfobase_entries, _ = parse_createinfobase_template(text)

    for name, arg in createinfobase_entries:
        table_entries.setdefault(name, []).append(("7.2.3", "CREATEINFOBASE", arg))

    old_glosses = {}
    if DST.exists():
        try:
            old = json.loads(DST.read_text(encoding="utf-8"))
            old_glosses = {
                k: v["gloss"] for k, v in old.get("ключи", {}).items() if "gloss" in v
            }
        except (OSError, json.JSONDecodeError):
            pass

    keys = {}
    for name, occurrences in sorted(table_entries.items()):
        sections = sorted({s for s, _, _ in occurrences})
        mode_tags = {mt for _, mt, _ in occurrences}
        modes = merge_modes(mode_tags)

        opts = []
        for _, _, syntax in occurrences:
            for opt in extract_opts(syntax):
                if opt not in opts:
                    opts.append(opt)
        opts.sort()

        arg = max((syntax.strip() for _, _, syntax in occurrences), key=len, default="")

        entry = {
            "arg": arg,
            "modes": modes,
            "opts": opts,
            "section": sections,
            "glued": name in glued,
        }
        if name in ARG_ONLY_IN_PROSE:
            entry["arg_прозой"] = ARG_ONLY_IN_PROSE[name]
        if name in old_glosses:
            entry["gloss"] = old_glosses[name]
        keys[name] = entry

    return keys


def main():
    keys = build_catalog()

    old_count = old_opts = 0
    if DST.exists():
        try:
            old = json.loads(DST.read_text(encoding="utf-8"))
            old_count = len(old.get("ключи", {}))
            old_opts = sum(len(v.get("opts", [])) for v in old.get("ключи", {}).values())
        except (OSError, json.JSONDecodeError):
            pass

    catalog = {
        "источник": (
            "1С:Предприятие 8.3.27, руководство администратора, приложение 7. "
            "Состав ключей собран программно (tools/build-cli-keys.py) из "
            "_its/cmdline/its-pril7-full.json; пояснения (gloss) — нами."
        ),
        "режимы": MODES_LIST,
        "шаблоны": TEMPLATES,
        "ключи": keys,
    }
    DST.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    verify_manifests()

    total_opts = sum(len(v["opts"]) for v in keys.values())
    multi_mode = sum(1 for v in keys.values() if len(v["modes"]) > 1)
    glued_count = sum(1 for v in keys.values() if v["glued"])
    print("ключей: было %d, стало %d" % (old_count, len(keys)))
    print("опций всего: было %d, стало %d" % (old_opts, total_opts))
    print("ключей с несколькими режимами: %d" % multi_mode)
    print("слитных ключей (glued): %d" % glued_count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
