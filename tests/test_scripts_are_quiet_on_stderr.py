"""Прибор, который зовёт агент, на успехе молчит в stderr.

## Почему это правило, а не придирка

PowerShell 5.1 оборачивает любой stderr нативной программы в
`NativeCommandError` и ставит `$?` в ложь — даже когда программа вернула
код 0. Значит предупреждение интерпретатора на выходе прибора выглядит
для агента как падение прибора.

Поймано живым прогоном 25.09.2026: в строке документации
`check-1c-cli.py` осталось `\\S`, Python 3.14 написал об этом
`SyntaxWarning`, и модель шесть раз подряд получила «ошибку» там, где был
код возврата 0. На седьмой она бросила приборы набора и написала свой
запускатель — то есть прибор сам вытолкнул её обходить себя.

Проверяется двумя способами. Первый — сборка каждого скрипта с
предупреждениями как ошибками: так ловятся предупреждения уровня
исходника (escape-последовательности и подобное), и ловятся у всех
скриптов разом, а не только у тех, что кто-то вспомнил прогнать. Второй —
запуск с `--help` у тех двух, которые агент зовёт напрямую: у них stderr
обязан быть пуст на самом деле, а не только в теории.

Запуск: python -m pytest tests/test_scripts_are_quiet_on_stderr.py -v
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

СКРИПТЫ = sorted(
    [p for p in ROOT.glob("skills/*/scripts/*.py")]
    + [p for p in ROOT.glob("tools/*.py")]
)

# Их агент зовёт своими руками, поэтому у них проверяется и живой запуск.
ЗОВЁТ_АГЕНТ = [
    ROOT / "skills" / "1c-build-and-db" / "scripts" / "check-1c-cli.py",
    ROOT / "skills" / "1c-build-and-db" / "scripts" / "run-1c.py",
]


def test_script_list_is_not_empty():
    """Сторож самого сторожа: пустой список молча прошёл бы за успех."""
    assert len(СКРИПТЫ) >= 10, СКРИПТЫ


@pytest.mark.parametrize("скрипт", СКРИПТЫ, ids=lambda p: p.name)
def test_no_source_level_warnings(скрипт):
    """Сборка с предупреждениями как ошибками: исходник чист."""
    готово = subprocess.run(
        [sys.executable, "-W", "error", "-c",
         "import sys,pathlib;"
         "src=pathlib.Path(sys.argv[1]).read_text(encoding='utf-8');"
         "compile(src, sys.argv[1], 'exec')",
         str(скрипт)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert готово.returncode == 0, готово.stderr


@pytest.mark.parametrize("скрипт", ЗОВЁТ_АГЕНТ, ids=lambda p: p.name)
def test_help_writes_nothing_to_stderr(скрипт):
    """--help не пишет в stderr ни байта: иначе PowerShell объявит отказ."""
    кэш = скрипт.parent / "__pycache__"
    if кэш.is_dir():
        for ф in кэш.glob("*"):
            ф.unlink()
    готово = subprocess.run(
        [sys.executable, str(скрипт), "--help"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert готово.stderr == "", готово.stderr
    assert готово.returncode == 0, готово.stdout
