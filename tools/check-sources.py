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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTION = re.compile(r"^##+\s*Что здесь необратимо\s*$", re.M)
NEXT_SECTION = re.compile(r"^##+\s", re.M)
SOURCE = re.compile(r"стандарт|глав[аеы]|приложени|руководств|проверено запуском", re.I)

# Ссылка вида «см. раздел «Название» в ядре» или «...в навыке». Именно так
# скилы указывают друг на друга по названию раздела, а не по markdown-ссылке.
SECTION_REF = re.compile(r"раздел\w*\s+«([^»]+)»\s+в\s+(?:ядре|навыке)", re.I)
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.M)


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
        if not SOURCE.search(para):
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


def find_dangling_refs(paths):
    """Возвращает список (файл, название) для ссылок на раздел по имени,
    которого нет ни в одном заголовке набора."""
    paths = list(paths)
    headings = collect_headings(paths)
    bad = []
    for p in paths:
        text = Path(p).read_text(encoding="utf-8")
        for m in SECTION_REF.finditer(text):
            name = m.group(1).strip()
            if name not in headings:
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
