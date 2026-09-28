"""Справочники навыков начинаются с метки порядка байтов UTF-8.

Codex не загружает навык сам: он даёт модели путь к SKILL.md, и файлы
модель открывает своей оболочкой. На Windows это PowerShell 5.1, и
`Get-Content` без `-Encoding` читает UTF-8 без BOM в кодировке ANSI
системы. Живой прогон 25.09.2026: агент прочёл навык как
«РџР°РєРµС‚РЅС‹Р№ РєРѕРЅС„РёРіСѓСЂР°С‚РѕСЂ» и работал по памяти. С BOM тот же
вызов читает текст верно — проверено на том же файле.

SKILL.md сюда не входит: перед его YAML-шапкой BOM может помешать
загрузчику навыков опознать шапку, и навык молча выпадет из каталога.
Это решается только живой проверкой в каждой среде, а не тестом.

Запуск: python -m pytest tests/test_references_have_bom.py -v
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
СПРАВОЧНИКИ = sorted(ROOT.glob("skills/*/references/*.md"))


def test_references_are_found():
    """Сторож без входа не сторожит ничего: файлов обязано быть много."""
    assert len(СПРАВОЧНИКИ) > 100, len(СПРАВОЧНИКИ)


@pytest.mark.parametrize("путь", СПРАВОЧНИКИ, ids=lambda п: "%s/%s" % (п.parent.parent.name, п.name))
def test_reference_starts_with_utf8_bom(путь):
    assert путь.read_bytes().startswith(b"\xef\xbb\xbf"), (
        "%s без BOM: PowerShell 5.1 прочтёт его как cp1251. Добавить: "
        "python tools/add-bom-to-references.py" % путь.relative_to(ROOT))
