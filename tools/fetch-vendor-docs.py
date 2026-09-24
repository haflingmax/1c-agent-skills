"""Выгрузка документации СУБД в локальный корпус: PostgreSQL и Microsoft Learn.

    python tools/fetch-vendor-docs.py            # всё, чего ещё нет
    python tools/fetch-vendor-docs.py --обновить # заново, включая скачанное
    python tools/fetch-vendor-docs.py --база pgdoc

## Зачем

Этап УГЛУБЛЕНИЕ-БД добавил четвёртую опору — документацию СУБД (решение 24).
Цитата из неё должна проверяться так же, как цитата из ИТС, а `check-quotes.py`
сверяет только с тем, что лежит в корпусе. Без этой выгрузки цитата
из документации PostgreSQL — утверждение без доказательства, а таких набор
не принимает.

## Что делает

Берёт список страниц из `docs/vendor-pages.json` (он коммитится, страницы —
нет, как и корпуса ИТС), скачивает каждую, вынимает из HTML текст статьи
и складывает в `_vendor/<база>-full.json` в том же виде, в каком лежат
корпуса ИТС: `{"docs": [{"id", "title", "url", "text"}]}`. Оттуда их читают
`its-search.py` и `check-quotes.py` — базами `pgdoc` и `mslearn`.

Список растёт вместе с набором: страница добавляется тогда, когда на неё
опирается утверждение, а не «про запас».

## Почему текст, а не HTML

Сверка цитат работает по тексту: разметка в цитату не попадает. Поэтому
из страницы выбрасываются навигация, оглавление и подвал, а остаётся то,
что человек читает как статью. У PostgreSQL это `div.SECT1`/`#docContent`,
у Microsoft Learn — `main`. Если разметка сайта изменится и выбранный узел
не найдётся, скрипт **падает**, а не пишет пустой документ: пустая статья
в корпусе означала бы «цитата не найдена» на верной цитате.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

if not os.environ.get("PYTHONIOENCODING"):
    for _поток in (sys.stdout, sys.stderr):
        try:
            _поток.reconfigure(encoding="utf-8", errors=_поток.errors)
        except (AttributeError, ValueError):
            pass

КОРЕНЬ = Path(__file__).resolve().parent.parent
СПИСОК = КОРЕНЬ / "docs" / "vendor-pages.json"
ВЫГРУЗКА = КОРЕНЬ / "_vendor"

# Узел со статьёй у каждого сайта свой; порядок — от точного к общему.
УЗЛЫ = {
    "pgdoc": ["div#docContent", "div.SECT1", "div.sect1", "main"],
    "mslearn": ["main#main", "main", "div.content"],
}
ЛИШНЕЕ = ["script", "style", "nav", "header", "footer", "noscript",
          "div.navheader", "div.navfooter", "table.navigation"]


def разобрать(html, база):
    """Текст статьи из страницы. Падает, если узел статьи не найден."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise SystemExit("[ошибка] нужен пакет beautifulsoup4: pip install beautifulsoup4")
    суп = BeautifulSoup(html, "html.parser")
    for образец in ЛИШНЕЕ:
        for узел in суп.select(образец):
            узел.decompose()
    for образец in УЗЛЫ[база]:
        узел = суп.select_one(образец)
        if узел is not None:
            текст = узел.get_text(" ", strip=True)
            if len(текст) > 500:
                return re.sub(r"\s+", " ", текст)
    raise SystemExit(
        "[ошибка] на странице базы %s не найден узел статьи (%s). "
        "Разметка сайта изменилась; пустой документ в корпусе читался бы "
        "как «цитаты нет в источнике»." % (база, ", ".join(УЗЛЫ[база])))


def скачать(url):
    import urllib.request
    запрос = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(запрос, timeout=60) as ответ:
        return ответ.read().decode("utf-8", errors="replace")


def прочитать_список():
    d = json.loads(СПИСОК.read_text(encoding="utf-8"))
    return d["страницы"], d.get("версии", {})


def путь_базы(база):
    return ВЫГРУЗКА / ("%s-full.json" % база)


def загруженное(база):
    п = путь_базы(база)
    if not п.is_file():
        return {}
    d = json.loads(п.read_text(encoding="utf-8"))
    return {с["id"]: с for с in d.get("docs", [])}


def сохранить(база, документы, версия):
    ВЫГРУЗКА.mkdir(exist_ok=True)
    путь_базы(база).write_text(json.dumps(
        {"версия": версия, "docs": list(документы.values())},
        ensure_ascii=False, indent=1), encoding="utf-8")


def main(argv=None):
    разбор = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    разбор.add_argument("--база", choices=sorted(УЗЛЫ))
    разбор.add_argument("--обновить", action="store_true",
                        help="перекачать и то, что уже лежит в корпусе")
    арг = разбор.parse_args(argv)

    страницы, версии = прочитать_список()
    базы = [арг.база] if арг.база else sorted({с["база"] for с in страницы})
    всего = новых = 0
    for база in базы:
        документы = загруженное(база)
        for с in [x for x in страницы if x["база"] == база]:
            всего += 1
            if с["id"] in документы and not арг.обновить:
                continue
            html = скачать(с["url"])
            текст = разобрать(html, база)
            документы[с["id"]] = {"id": с["id"], "title": с["заголовок"],
                                  "url": с["url"], "text": текст}
            новых += 1
            print("взято %-22s %7d знаков  %s" % (с["id"], len(текст), с["url"]))
        сохранить(база, документы, версии.get(база, ""))
        print("база %s: документов %d, файл %s"
              % (база, len(документы), путь_базы(база).name))
    print("страниц в списке: %d, скачано сейчас: %d" % (всего, новых))
    return 0


if __name__ == "__main__":
    sys.exit(main())
