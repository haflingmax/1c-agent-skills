"""C-1: инструмент, который пишет в skills/, обязан проверять записанное.

Находка C-1 финального ревью (`.superpowers/sdd/2026-08-23-core-remediation/
final-findings.md`) была не про один скрипт. `tools/measure-trigger.ps1` вернул
бы в `SKILL.md` фронтматтер со сломанным YAML — ровно ту Н-01, ради которой
заведён `tools/check-manifests.py`, — и никто бы этого не заметил: замер
записанное не перечитывал, `check-skills.py` разбирает фронтматтер регуляркой
и такую порчу пропускает (проверено: на испорченном файле он вернул 0), а сам
`check-manifests.py` никто не звал.

Правило, закрывающее класс: **любой инструмент, который пишет в `skills/`,
заканчивается прогоном `tools/check-manifests.py` и падает при ненулевом коде.**

Автоматически отличить «пишет в skills/» от «копирует из skills/ наружу»
статически нельзя — `install-skills.ps1` и `run-acceptance.ps1` тоже упоминают
и `skills`, и запись, но пишут в каталоги сред. Поэтому реестр ниже заполняется
руками, а тест сторожит не догадку, а полноту: новый файл в `tools/` роняет
прогон, пока автор не отнесёт его к одному из двух классов явно.
"""
import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"

# Пишут в skills/ — обязаны заканчиваться check-manifests.py.
WRITES_INTO_SKILLS = {
    "build-cli-keys.py":
        "пересобирает skills/1c-build-and-db/scripts/cli-keys.json",
    "measure-trigger.ps1":
        "переписывает description в skills/developing-1c-configurations/SKILL.md",
}

# В skills/ не пишут. Причина названа поимённо, а не подразумевается.
READS_ONLY = {
    "check-skills.py": "только читает навыки",
    "check-sources.py": "только читает навыки",
    "check-manifests.py": "сам и есть та проверка",
    "install-skills.ps1": "копирует ИЗ skills/ в каталоги сред",
    "run-acceptance.ps1": "копирует ИЗ skills/ и гоняет агентов",
    "run-prompt.ps1": "гоняет один промпт, файлов набора не трогает",
    "prove-blocking-rules.ps1": "гоняет 1cv8 во временном каталоге",
}


def tool_files():
    return sorted(
        p.name for p in TOOLS.iterdir()
        if p.is_file() and p.suffix in (".py", ".ps1")
    )


def read(name):
    return (TOOLS / name).read_text(encoding="utf-8-sig")


def test_every_tool_is_classified():
    """Новый инструмент обязан быть отнесён к одному из двух классов."""
    classified = set(WRITES_INTO_SKILLS) | set(READS_ONLY)
    actual = set(tool_files())
    assert actual == classified, (
        "реестр tools/ разошёлся с каталогом: не отнесены %s, лишние в реестре %s"
        % (sorted(actual - classified), sorted(classified - actual)))


@pytest.mark.parametrize("name", sorted(WRITES_INTO_SKILLS))
def test_writer_ends_with_manifest_check(name):
    """C-1: пишет в skills/ — значит зовёт check-manifests.py."""
    text = read(name)
    assert "check-manifests.py" in text, (
        "%s пишет в skills/ (%s), но не проверяет записанное "
        "tools/check-manifests.py" % (name, WRITES_INTO_SKILLS[name]))


def test_build_cli_keys_falls_on_nonzero_manifest_check(monkeypatch):
    """Ненулевой код проверки обязан ронять сборщик, а не логироваться."""
    spec = importlib.util.spec_from_file_location(
        "build_cli_keys", TOOLS / "build-cli-keys.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_cli_keys"] = mod
    spec.loader.exec_module(mod)

    class Fake:
        returncode = 1
        stdout = "[!] что-то не так\n"
        stderr = ""

    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: Fake())
    with pytest.raises(SystemExit) as e:
        mod.verify_manifests()
    assert e.value.code == 3

    class Ok:
        returncode = 0
        stdout = "манифесты проверены, нарушений: 0\n"
        stderr = ""

    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: Ok())
    mod.verify_manifests()  # нулевой код — молча идём дальше


def test_measure_trigger_holds_no_description_constant():
    """C-1 напрямую: текста описания в скрипте замера быть не должно.

    Константа $NewDescription разошлась с поставляемым SKILL.md и возвращала
    в набор двоеточие. Сторожим не конкретную строку, а сам приём: длинное
    строковое присваивание переменной с «Description» в имени.
    """
    text = read("measure-trigger.ps1")
    bad = [
        line.strip() for line in text.splitlines()
        if re.match(r"^\s*\$\w*Description\w*\s*=\s*['\"].{60,}", line)
    ]
    assert not bad, (
        "в tools/measure-trigger.ps1 снова зашит текст описания: %s" % bad)


def test_measure_trigger_write_preserves_line_ending():
    """Запись description не имеет права ронять CR у своей строки.

    Регулярка берётся из самого скрипта, а не переписывается сюда: тест
    проверяет то, чем скрипт пользуется. `.*` в многострочном режиме съедает
    `\\r` перед `\\n` — и запись молча превращала CRLF в LF. Семантика
    `(?m)^` и `[^\\r\\n]*` у .NET и у `re` здесь совпадает.
    """
    text = read("measure-trigger.ps1")
    m = re.search(r"\$updated = \$before -replace '([^']+)'", text)
    assert m, "не найдена регулярка записи description"
    pattern = m.group(1)
    sample = "---\r\nname: x\r\ndescription: старое\r\n---\r\nтело\r\n"
    out = re.sub(pattern, "description: новое", sample)
    assert out == "---\r\nname: x\r\ndescription: новое\r\n---\r\nтело\r\n", (
        "регулярка %r портит перевод строки: %r" % (pattern, out))
