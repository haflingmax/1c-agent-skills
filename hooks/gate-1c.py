"""Ворота: команда 1cv8 не запускается, не пройдя проверку.

## Зачем

Набор читают по диагонали. Агент инцидента 28.08.2026 остановился
на описании навыка, не открыл ни тела, ни справочников, не запустил
проверяльщик — и полтора часа бился в модальный диалог, которого не видел.
Проверяльщик отказал бы на первой же его команде (код 1, «CONFIG не режим
запуска»). Не хватало не знания, а принуждения.

Ворота работают, даже если модель не открывала навык вообще.

## Граница

Арбитром «похоже ли это на запуск 1cv8» служит сам проверяльщик, а не
регулярка здесь. Подбор по имени в этом наборе — известная ловушка
(`docs/debt.md`, раздел 5): `grep 1cv8 log.txt` регулярка поймает,
и ворота начнут мешать законному. Проверяльщик на такую команду отвечает
кодом K017 и кодом возврата 0, и хук её пропускает.

По той же причине пропускается и запуск через обёртку
(`python run-1c.py "1cv8 …"`): первое слово там — `python`, а не `1cv8`.
Двойных ворот быть не должно, иначе единственный рекомендуемый способ
запуска оказался бы невозможен.

## Чего хук не делает

Не судит `ibcmd`, `rac` и `ras` — проверяльщик не знает их состава ключей,
и ворота не выдают незнание за разрешение.

Не роняет работу. Любая своя беда — пропуск: инструмент, который ломает
чужую работу собственной ошибкой, хуже отсутствующего.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

КОРЕНЬ = Path(os.environ.get("CLAUDE_PLUGIN_ROOT",
                             Path(__file__).resolve().parent.parent))
ПРОВЕРЯЛЬЩИК = (КОРЕНЬ / "skills" / "1c-build-and-db" / "scripts"
                / "check-1c-cli.py")


def решение(payload):
    """Готовый ответ Claude Code либо None, если вмешиваться не нужно."""
    if payload.get("tool_name") != "Bash":
        return None
    команда = (payload.get("tool_input") or {}).get("command") or ""
    if "1cv8" not in команда.lower():
        return None
    if not ПРОВЕРЯЛЬЩИК.is_file():
        return None

    готово = subprocess.run(
        [sys.executable, str(ПРОВЕРЯЛЬЩИК), команда],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    if готово.returncode == 0:
        return None

    причина = (
        "Команда 1cv8 не прошла проверку и не запущена.\n\n"
        "%s\n\n"
        "Это ворота набора 1c-agent-skills. Ключи командной строки 1С "
        "не пишутся по памяти: их 140, они похожи друг на друга, "
        "и выдуманный ключ выглядит правдоподобно. Разбор — в навыке "
        "1c-build-and-db: тело SKILL.md и references/load-configuration.md. "
        "Запускать через scripts/run-1c.py — он проверит команду, дождётся "
        "процесса (1cv8.exe возвращает управление немедленно и без этого "
        "не оставляет ни журнала, ни кода возврата) и объяснит зависание."
        % готово.stdout.strip())
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": причина,
        "additionalContext": причина,
    }}


def main():
    try:
        сырое = os.environ.get("HOOK_PAYLOAD") or sys.stdin.read() or "{}"
        payload = json.loads(сырое)
        if isinstance(payload, dict):
            ответ = решение(payload)
            if ответ is not None:
                # ensure_ascii=True (по умолчанию) намеренно: вывод хука
                # всегда уходит в трубу, а Python на Windows берёт для трубы
                # ANSI-кодировку системы — кириллица приехала бы искажённой
                # (тот же дефект описан в шапке check-1c-cli.py). JSON
                # с \uXXXX читается любым разборщиком и от кодовой страницы
                # не зависит вовсе.
                print(json.dumps(ответ, separators=(",", ":")))
    except Exception:
        # Ворота не имеют права ломать работу: любая своя беда — пропуск.
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
