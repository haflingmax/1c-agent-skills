"""Решение ворот: что хук отвечает на готовый payload.

Хук — единственное место набора, работающее без участия модели. Поэтому
проверяется он не прогоном агента, а прямым вызовом на подготовленных
payload: так видно и отказ, и — важнее — что законное проходит.

Третий критерий успеха этапа звучит так: «ворота не мешают законному».
Прибор, который отказывает верным командам, снимут через неделю, и это
будет правильно. Тесты ниже сторожат именно это.

Запуск: python -m pytest tests/test_gate_hook.py -v
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "hooks" / "gate-1c.py"

spec = importlib.util.spec_from_file_location("gate_1c", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["gate_1c"] = mod
spec.loader.exec_module(mod)


def payload(команда, инструмент="Bash"):
    return {"hook_event_name": "PreToolUse", "tool_name": инструмент,
            "tool_input": {"command": команда}}


def test_incident_command_is_denied():
    """Команда инцидента 28.08.2026 отклоняется до запуска.

    Именно она полтора часа била в модальный диалог: CONFIG — не режим
    запуска, и проверяльщик сказал бы это сразу, если бы его вызвали.
    Ворота вызывают его за модель.
    """
    ответ = mod.решение(payload(
        "1cv8 CONFIG /F D:/1C/base/trade /LoadConfigFromFiles D:/src /UpdateDBCfg"))
    assert ответ is not None
    вывод = ответ["hookSpecificOutput"]
    assert вывод["permissionDecision"] == "deny"
    assert "K002" in вывод["permissionDecisionReason"]


def test_mention_of_1cv8_is_not_a_launch():
    """grep 1cv8 log.txt — законная команда, ворота её пропускают.

    Подбор по имени в этом наборе — известная ловушка (docs/debt.md,
    раздел 5). Арбитром служит проверяльщик: на чужой инструмент он
    отвечает K017 и кодом 0.
    """
    assert mod.решение(payload("grep 1cv8 log.txt")) is None


def test_wrapper_invocation_is_not_gated(tmp_path):
    """Запуск через обёртку не блокируется, хотя содержит подстроку 1cv8.

    Найдено на предполётной сверке плана: команда
    `python scripts/run-1c.py "1cv8 DESIGNER …"` проходит предфильтр хука.
    Двойных ворот быть не должно — иначе единственный рекомендуемый способ
    запуска оказался бы невозможен.
    """
    команда = ('python scripts/run-1c.py "1cv8 DESIGNER /F d:/base '
               '/LoadCfg a.cf /UpdateDBCfg -Dynamic- /DisableStartupDialogs '
               '/Out log.txt"')
    assert mod.решение(payload(команда)) is None


def test_ordinary_command_passes_untouched():
    """Обычная работа воротами не задевается."""
    assert mod.решение(payload("git status --short")) is None


def test_valid_command_passes(tmp_path):
    """Верная команда проходит: ворота отказывают только непрошедшим."""
    команда = ('1cv8 DESIGNER /F "%s" /N Admin /P"" /DumpCfg out.cf '
               '/DisableStartupDialogs /Out log.txt' % (tmp_path / "нет-базы"))
    assert mod.решение(payload(команда)) is None


def test_quotes_inside_command_do_not_leak_secrets():
    """Пароль из команды не попадает в текст отказа.

    Отказ читает и модель, и человек, и он остаётся в расшифровке
    разговора. Пароль там не нужен.
    """
    ответ = mod.решение(payload(
        '1cv8 CONFIG /F d:/base /P"пароль с пробелом" /LoadCfg a.cf'))
    assert ответ is not None
    assert "пароль с пробелом" not in ответ["hookSpecificOutput"]["permissionDecisionReason"]


def test_other_tools_are_ignored():
    """Хук стоит на Bash; Read и Write его не касаются."""
    assert mod.решение(payload("что угодно", инструмент="Read")) is None


def test_missing_command_is_not_a_crash():
    """Payload без команды не роняет хук: ворота не имеют права ломать работу."""
    assert mod.решение({"tool_name": "Bash", "tool_input": {}}) is None
    assert mod.решение({"tool_name": "Bash"}) is None


def test_shim_has_no_carriage_returns():
    """Шим обязан лежать с LF: bash падает на CRLF.

    Не RED→GREEN, а сторож опасности, проверенной руками: в репозитории
    core.autocrlf=true, и без .gitattributes следующая выдача файла
    подставила бы CRLF. Ворота исчезли бы молча — bash сказал бы
    «$'\r': command not found» и вышел, а Claude Code принял бы пустой
    вывод за «возражений нет».
    """
    шим = ROOT / "hooks" / "gate-1c.sh"
    assert b"\r\n" not in шим.read_bytes(), (
        "у %s перевод строки CRLF — bash такой файл не выполнит" % шим)
