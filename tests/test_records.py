"""Записи о работе доведены: реестр закрытий и чекбоксы плана (M-7).

M-7 финального ревью: в плане доработки лежали 46 неотмеченных чекбоксов и ни
одного отмеченного после полного исполнения, а общий реестр `docs/plan.md`
был заведён только для находок задачи 5 — Н-01…Н-11 и 23 мелкие в него не
попали, хотя спека требует «номера в общем реестре дефектов и закрываются
поимённо».

Тест сторожит не текст закрытий (он свободный), а полноту: ни одна находка
ветки не должна выпасть из реестра.

Запуск: python -m pytest tests/test_records.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "docs" / "plan.md"
TASK_PLAN = ROOT / "docs" / "plans" / "2026-08-23-core-remediation.md"
REVIEW = ROOT / "docs" / "reviews" / "2026-08-23-core-review.md"


def plan_text():
    return PLAN.read_text(encoding="utf-8")


def test_review_still_declares_fourteen_and_thirty():
    """Числа берутся из документа находок, а не зашиты сюда наугад."""
    text = REVIEW.read_text(encoding="utf-8")
    assert len(set(re.findall(r"^### (Н-\d\d)\.", text, re.M))) == 14
    assert len(set(re.findall(r"^### (М-\d\d)\.", text, re.M))) == 30


@pytest.mark.parametrize("num", ["Н-%02d" % i for i in range(1, 15)])
def test_every_major_finding_is_in_the_registry(num):
    assert num in plan_text(), "%s не попала в реестр docs/plan.md" % num


@pytest.mark.parametrize("num", ["М-%02d" % i for i in range(1, 31)])
def test_every_minor_finding_is_in_the_registry(num):
    assert num in plan_text(), "%s не попала в реестр docs/plan.md" % num


@pytest.mark.parametrize("num", ["C-1"] + ["I-%d" % i for i in range(1, 8)]
                         + ["M-%d" % i for i in range(1, 10)])
def test_every_final_review_finding_is_in_the_registry(num):
    assert re.search(r"\b%s\b" % re.escape(num), plan_text()), (
        "%s финального ревью не попала в реестр docs/plan.md" % num)


def test_deferred_finding_is_an_open_item_not_a_closure():
    """M-3 отложена сознательно — она обязана стоять открытой, а не закрытой."""
    text = plan_text()
    assert "~~M-3~~" not in text, "M-3 помечена закрытой, хотя отложена"
    assert "О-5" in text, "M-3 не заведена открытым пунктом"
    open_block = text.split("## Открытые вопросы", 1)[1].split("##", 1)[0]
    assert "О-5" in open_block, "О-5 стоит не в разделе открытых вопросов"


def test_task_plan_checkboxes_are_marked():
    """46 шагов плана исполнены — ни одного неотмеченного не осталось."""
    text = TASK_PLAN.read_text(encoding="utf-8")
    unmarked = re.findall(r"^\s*- \[ \]", text, re.M)
    marked = re.findall(r"^\s*- \[x\]", text, re.M)
    assert not unmarked, "неотмеченных шагов: %d" % len(unmarked)
    assert len(marked) == 46, len(marked)
