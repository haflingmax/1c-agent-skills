"""Проверка прослеживаемости утверждений о необратимости.

Раздел «Что здесь необратимо» в любом навыке обязан ссылаться на источник:
стандарт, главу руководства либо пометку «проверено запуском». Проверяется
наличие ссылки, а не её смысл — смысл проверяет человек.

Вторая проверка ловит другой класс дефекта прослеживаемости: ссылку на раздел
другого навыка по имени («см. раздел «Название» в ядре»), для которого в
наборе навыков больше нет заголовка с таким названием. Обычная проверка
markdown-ссылок такое не видит: здесь нет `[текст](файл.md)`, есть только
название раздела в кавычках-ёлочках.

    python tools/check-sources.py
"""
import re
import os
import sys
from pathlib import Path

# Вывод этих скриптов — кириллица и знаки «», «—», «→». Пока stdout остаётся
# окном консоли, беды нет: Python 3.14 на Windows пишет туда через WriteConsoleW
# и отдаёт utf-8 при любой кодовой странице — проверено запуском 25.08.2026 под
# chcp 866, 1251 и 65001, во всех трёх sys.stdout.encoding == 'utf-8'.
#
# Ломается ПЕРЕНАПРАВЛЕНИЕ: когда вывод уходит в файл или в трубу, Python берёт
# ANSI-кодировку системы (здесь cp1251), и первый же знак вне неё роняет скрипт
# трассировкой вместо отчёта. Так падал check-1c-cli.py, отгружаемый внутри
# навыка, и так its-search.py не мог отдать даже --help.
#
# Две оговорки, каждая из-за собственной ошибки первой редакции:
#   errors= передаём прежний — reconfigure(encoding=...) молча ставит strict,
#   а интерпретатор держит на stdout surrogateescape и на stderr
#   backslashreplace нарочно, чтобы печать имени файла с одиночным суррогатом
#   (обычное дело в Windows) не роняла сам вывод;
#   при заданной PYTHONIOENCODING не трогаем ничего — иначе у человека
#   не остаётся способа задать кодировку под своего потребителя вывода.
if not os.environ.get("PYTHONIOENCODING"):
    for _поток in (sys.stdout, sys.stderr):
        try:
            _поток.reconfigure(encoding="utf-8", errors=_поток.errors)
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parent.parent
SECTION = re.compile(r"^##+\s*Что здесь необратимо\s*$", re.M)
NEXT_SECTION = re.compile(r"^##+\s", re.M)

# Прослеживаемость проверялась наличием слова, а не разрешимостью ссылки
# (находка М-27 docs/reviews/2026-08-23-core-review.md): абзац со словом
# «руководство» проходил, даже если ни глава, ни раздел не названы — слово
# ничего не даёт прочитать и проверить. Настоящая ссылка на документ узнаётся
# по номеру рядом со словом-маркером («приложение 7», «раздел 6.7», «глава 5»)
# либо по названию в кавычках-ёлочках («стандарт «Название»»); настоящая
# ссылка на прогон — по markdown-ссылке или названию раздела в кавычках рядом
# с «проверено запуском», а не по самой фразе.
SOURCE_DOC = re.compile(r"(стандарт|глав[аеы]|приложени\w*|раздел\w*|руководств\w*"
                         r"|методичк\w*)"
                         r"(\s+\S+){0,4}?\s+(\d|«)", re.I)

# Поправка 26.08.2026. Три формы адреса, которыми набор пользуется чаще
# слова-маркера, проверке не были известны: параграф руководства («§5.5.23»),
# номер стандарта («`std789`») и номер методички в скобке («(2288)»).
# Из-за этого пять абзацев в трёх навыках считались бессточными — при том
# что адрес в них стоял, — и код возврата был красным без причины.
# Адрес обязан нести номер: «§» или «std» без цифр ничего не даёт прочитать.
SOURCE_ADDRESS = re.compile(r"§\s*\d|\bstd\s?\d{3}\b|\(\d{4}[,)]", re.I)
SOURCE_RUN = re.compile(r"проверено запуском")

# Абзац, который называет себя выводом набора. Правило требует источник
# у каждого утверждения раздела, и это верно для утверждений о платформе;
# но абзац, прямо говорящий «это наш вывод, а не источник», выполняет ровно
# то, ради чего правило существует, — не даёт принять рассуждение набора
# за цитату. Формула требуется целиком: одного слова «вывод» мало, иначе
# она станет отговоркой.
OWN_CONCLUSION = re.compile(r"вывод\s+набора,\s+а\s+не\s+источника", re.I)
RESOLVABLE_POINTER = re.compile(r"\]\([^)]+\)|«[^»]+»")

# Ссылка вида «см. раздел «Название» в ядре» или «...в навыке». Именно так
# скилы указывают друг на друга по названию раздела, а не по markdown-ссылке.
SECTION_REF = re.compile(r"раздел\w*\s+«([^»]+)»\s+в\s+(?:ядре|навыке)", re.I)
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.M)

# Маршрутная таблица вида «| Раздел | Когда нужен | Навык |» (см. developing-
# 1c-configurations/SKILL.md, раздел «Разделы»): первый столбец — законное имя
# раздела, не обязанное совпадать ни с одним markdown-заголовком. Без этого
# «см. раздел «Сборка и база» в навыке» ловится как висячее, хотя это просто
# другой, действующий способ адресации.
ROUTE_TABLE_HEADER = re.compile(r"^\|\s*Раздел[ы]?\s*\|.*$\n^\|[\s:|-]+\|\s*$\n", re.M | re.I)


def check_file(path):
    """Возвращает список абзацев без источника."""
    text = Path(path).read_text(encoding="utf-8")
    m = SECTION.search(text)
    if not m:
        return []
    rest = text[m.end():]
    nxt = NEXT_SECTION.search(rest)
    body = rest[: nxt.start()] if nxt else rest
    bad = []
    for para in [p.strip() for p in body.split("\n\n") if p.strip()]:
        # Порог отсекает случайные обрывки (маркер списка, «---»), не сами
        # короткие утверждения — реальные абзацы в разделе длиннее сотни знаков.
        if len(para) < 20:
            continue
        # Источник разрешим, если рядом со словом-маркером стоит номер
        # (глава/раздел/приложение документа), либо «проверено запуском»
        # сопровождается ссылкой — markdown-ссылкой или названием раздела в
        # кавычках-ёлочках, а не голым словом.
        traceable = bool(SOURCE_DOC.search(para)) or bool(
            SOURCE_ADDRESS.search(para)) or bool(
            OWN_CONCLUSION.search(para)) or (
            bool(SOURCE_RUN.search(para)) and bool(RESOLVABLE_POINTER.search(para)))
        if not traceable:
            bad.append(para.replace("\n", " ")[:90])
    return bad


def collect_headings(paths):
    """Возвращает множество названий всех заголовков across переданных файлов."""
    names = set()
    for p in paths:
        text = Path(p).read_text(encoding="utf-8")
        for m in HEADING.finditer(text):
            names.add(m.group(1).strip())
    return names


def collect_route_names(paths):
    """Возвращает имена разделов из маршрутных таблиц («| Раздел | ... |»)."""
    names = set()
    for p in paths:
        text = Path(p).read_text(encoding="utf-8")
        for m in ROUTE_TABLE_HEADER.finditer(text):
            for line in text[m.end():].splitlines():
                if not line.startswith("|"):
                    break
                cells = line.strip().strip("|").split("|")
                if cells and cells[0].strip():
                    names.add(cells[0].strip().strip("*`"))
    return names


def find_dangling_refs(paths):
    """Возвращает список (файл, название) для ссылок на раздел по имени,
    которого нет ни среди заголовков, ни среди имён в маршрутных таблицах."""
    paths = list(paths)
    names = collect_headings(paths) | collect_route_names(paths)
    bad = []
    for p in paths:
        text = Path(p).read_text(encoding="utf-8")
        for m in SECTION_REF.finditer(text):
            name = m.group(1).strip()
            if name not in names:
                bad.append((Path(p), name))
    return bad


def main():
    total = 0
    for md in sorted((ROOT / "skills").rglob("*.md")):
        bad = check_file(md)
        if bad:
            print("[!] %s" % md.relative_to(ROOT))
            for b in bad:
                print("      без источника: %s…" % b)
            total += len(bad)

    refs_bad = find_dangling_refs(sorted((ROOT / "skills").rglob("*.md")))
    for path, name in refs_bad:
        print("[!] %s" % path.relative_to(ROOT))
        print("      висячая ссылка на раздел: «%s»" % name)
    total += len(refs_bad)

    print()
    print("утверждений без источника: %d" % (total - len(refs_bad)))
    print("висячих ссылок на разделы: %d" % len(refs_bad))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
