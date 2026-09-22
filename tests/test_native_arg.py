"""Промпт доходит до агента целым, даже с двойными кавычками внутри.

22.09.2026 проверочный промпт V1 пришёл во все три среды без кавычек
вокруг "РегистрНакопления.ТоварыНаСкладах": Windows PowerShell 5.1 не
экранирует кавычки, собирая командную строку нативной программы. Замер
на node: 'a "b c" d' доходит как 'a b' — промпт обрезан молча.

Тест гоняет `ConvertTo-NativeArgument` через настоящий PowerShell 5.1
и настоящий node — тот же путь, каким промпт идёт к kilo.exe, claude.exe
и к node за codex.ps1.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

КОРЕНЬ = Path(__file__).resolve().parent.parent
ФУНКЦИЯ = КОРЕНЬ / "tools" / "native-arg.ps1"

pytestmark = pytest.mark.skipif(
    not (shutil.which("powershell") and shutil.which("node")),
    reason="нужны Windows PowerShell и node")

СТРОКИ = [
    'a "b c" d',
    'Блокировка.Добавить("РегистрНакопления.ТоварыНаСкладах");',
    'history="24" и «ёлочки»',
    'путь C:\\dir\\ и \\"цитата\\"',
    'конец со слэшем C:\\temp\\',
    'без кавычек вовсе',
]


def прогнать(текст, экранировать=True):
    """Что получит нативная программа в argv[1]."""
    вход = КОРЕНЬ / ".pytest-native-arg.txt"
    вход.write_text(текст, encoding="utf-8")
    try:
        преобразование = "ConvertTo-NativeArgument $t" if экранировать else "$t"
        скрипт = (
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
            ". '%s'; "
            "$t = [IO.File]::ReadAllText('%s', [Text.Encoding]::UTF8); "
            "$a = %s; "
            "& node -e \"process.stdout.write(JSON.stringify(process.argv[1]))\" $a"
            % (ФУНКЦИЯ, вход, преобразование))
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", скрипт],
            capture_output=True, timeout=60)
        return json.loads(r.stdout.decode("utf-8"))
    finally:
        вход.unlink()


@pytest.mark.parametrize("текст", СТРОКИ)
def test_строка_доходит_целой(текст):
    assert прогнать(текст) == текст


def test_без_экранирования_промпт_режется():
    """Сама поломка: без функции кавычки теряются, а промпт обрезается."""
    assert прогнать('a "b c" d', экранировать=False) != 'a "b c" d'


def test_прогон_передаёт_агентам_экранированный_промпт():
    """Все три вызова сред в run-prompt.ps1 получают $PromptArg, а не $Prompt."""
    т = (КОРЕНЬ / "tools" / "run-prompt.ps1").read_text(encoding="utf-8-sig")
    assert "ConvertTo-NativeArgument $Prompt" in т
    for вызов in ("--format json $Prompt ", "claude -p $Prompt ",
                  "--skip-git-repo-check $Prompt "):
        assert вызов not in т, "среда получает неэкранированный промпт: " + вызов
