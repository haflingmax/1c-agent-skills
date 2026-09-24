"""Корпус документации СУБД: выгрузка, регистрация баз, сверка цитат.

Этап УГЛУБЛЕНИЕ-БД добавил четвёртую опору — документацию PostgreSQL
и Microsoft Learn (решение 24). Цитата из неё обязана проверяться так же,
как цитата из ИТС: `check-quotes.py` сверяет с корпусом, а корпус берётся
из `_vendor/`.

Главное, что стережёт этот файл, — **громкий отказ на изменившейся
разметке**. Если сайт переедет и узел статьи не найдётся, выгрузка должна
падать: пустая статья в корпусе читалась бы как «цитаты нет в источнике»,
то есть верная цитата выглядела бы выдуманной.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

КОРЕНЬ = Path(__file__).resolve().parent.parent


def модуль(имя_файла, имя):
    спец = importlib.util.spec_from_file_location(имя, КОРЕНЬ / "tools" / имя_файла)
    м = importlib.util.module_from_spec(спец)
    sys.modules[имя] = м
    спец.loader.exec_module(м)
    return м


ВЫГРУЗКА = модуль("fetch-vendor-docs.py", "fetch_vendor_docs")
ПОИСК = модуль("its-search.py", "its_search_vendor")

СТРАНИЦА_PG = """
<html><body>
 <div class="navheader"><table class="navigation"><tr><td>Prev Up Next</td></tr></table></div>
 <div id="docContent"><div class="SECT1"><h2>13.2. Transaction Isolation</h2>
 <p>%s</p></div></div>
 <div class="navfooter">Submit correction</div>
 <script>var x = 1;</script>
</body></html>""" % ("The SQL standard defines four levels of transaction isolation. " * 20)


def test_страница_превращается_в_текст_статьи():
    текст = ВЫГРУЗКА.разобрать(СТРАНИЦА_PG, "pgdoc")
    assert "Transaction Isolation" in текст
    assert "Prev Up Next" not in текст, "навигация в корпус не идёт"
    assert "Submit correction" not in текст and "var x" not in текст


def test_изменившаяся_разметка_роняет_выгрузку():
    """Пустая статья в корпусе — это «цитаты нет в источнике» на верной цитате."""
    with pytest.raises(SystemExit):
        ВЫГРУЗКА.разобрать("<html><body><div class='other'>мало текста</div></body></html>",
                           "pgdoc")


def test_короткий_узел_не_считается_статьёй():
    страница = "<html><body><div id='docContent'>13.2.</div><main>%s</main></body></html>" % (
        "Real article text. " * 60)
    текст = ВЫГРУЗКА.разобрать(страница, "pgdoc")
    assert "Real article text" in текст, (
        "узел с парой слов — это заголовок или хлебные крошки, а не статья")


def test_список_страниц_согласован_с_разбором():
    d = json.loads((КОРЕНЬ / "docs" / "vendor-pages.json").read_text(encoding="utf-8"))
    страницы = d["страницы"]
    assert страницы, "список страниц пуст — корпусу неоткуда взяться"
    номера = [с["id"] for с in страницы]
    assert len(номера) == len(set(номера)), "повторяющийся id страницы"
    for с in страницы:
        assert с["база"] in ВЫГРУЗКА.УЗЛЫ, "для базы %s не задан узел статьи" % с["база"]
        assert с["url"].startswith("https://"), с["url"]
        assert с["заголовок"].strip()
    for база in {с["база"] for с in страницы}:
        assert d["версии"].get(база), (
            "у базы %s не записана версия документации: без неё цитата "
            "не привязана к версии СУБД" % база)


def test_базы_субд_зарегистрированы_в_поиске():
    for база in ("pgdoc", "mslearn"):
        assert база in ПОИСК.БАЗЫ, "база %s не видна поиску и сверке цитат" % база
        путь = ПОИСК.БАЗЫ[база][0]
        assert путь.parent.name == "_vendor", (
            "выгрузка документации СУБД лежит в _vendor/, как корпуса ИТС в _its/")


def test_выгрузка_не_попадает_в_репозиторий():
    """Страницы вендоров не коммитятся — коммитится только их список."""
    assert "_vendor/" in (КОРЕНЬ / ".gitignore").read_text(encoding="utf-8")


@pytest.mark.skipif(not (КОРЕНЬ / "_vendor" / "pgdoc-full.json").is_file(),
                    reason="корпус СУБД не выгружен на этой машине")
def test_цитата_из_документации_субд_проверяема():
    """Сверка цитат обязана видеть корпус СУБД, иначе цитата из него «не найдена»."""
    cq = модуль("check-quotes.py", "check_quotes_vendor")
    _по_номеру, стог = cq.корпуса()
    фраза = cq.нормализовать("Read Committed is the default isolation level in PostgreSQL")
    assert стог and фраза in стог
