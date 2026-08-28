# -*- coding: utf-8 -*-
"""Проверки правки списка разрешений Kilo.

Правка идёт по чужому конфигу владельца, поэтому проверяется не «сработало
ли», а «не испортило ли»: комментарии на месте, посторонние блоки не тронуты,
повторный запуск ничего не меняет, а на непонятном файле инструмент
отказывается работать, но не падает.
"""
import json
import os
import re
import subprocess
import sys

import pytest

КОРЕНЬ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
СКРИПТ = os.path.join(КОРЕНЬ, "tools", "allow-skills-in-kilo.py")

КОНФИГ = """\
{
  // Комментарий владельца, который нельзя потерять.
  "permissions": {
    "bash": "ask",
    "skill": {
      "*": "ask",
      "developing-1c-configurations": "allow",
      "writing-plans": "allow"
    },
    "websearch": "ask"
  },
  /* Блочный комментарий тоже остаётся. */
  "model": "opus"
}
"""


def навыки(tmp_path, имена):
    каталог = tmp_path / "skills"
    for и in имена:
        d = каталог / и
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: %s\n---\n" % и, encoding="utf-8")
    return str(каталог)


def запуск(каталог, конфиг, *ещё):
    return subprocess.run(
        [sys.executable, СКРИПТ, "--каталог", каталог, "--конфиг", str(конфиг)] + list(ещё),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=КОРЕНЬ)


def блок(текст):
    м = re.search(r'"skill"\s*:\s*\{(.*?)\n    \}', текст, re.S)
    assert м, "блок skill не найден"
    return м.group(1)


def test_добавляет_только_недостающие(tmp_path):
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text(КОНФИГ, encoding="utf-8")
    к = навыки(tmp_path, ["1c-queries", "developing-1c-configurations", "1c-security"])

    р = запуск(к, конфиг)
    assert р.returncode == 0, р.stderr

    тело = блок(конфиг.read_text(encoding="utf-8"))
    assert '"1c-queries": "allow"' in тело
    assert '"1c-security": "allow"' in тело
    # уже разрешённый не задваивается
    assert тело.count('"developing-1c-configurations"') == 1


def test_чужое_не_тронуто(tmp_path):
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text(КОНФИГ, encoding="utf-8")
    к = навыки(tmp_path, ["1c-queries"])

    запуск(к, конфиг)
    новый = конфиг.read_text(encoding="utf-8")

    assert "// Комментарий владельца, который нельзя потерять." in новый
    assert "/* Блочный комментарий тоже остаётся. */" in новый
    assert '"bash": "ask"' in новый
    assert '"websearch": "ask"' in новый
    assert '"model": "opus"' in новый
    assert '"writing-plans": "allow"' in новый


def test_результат_остаётся_разбираемым(tmp_path):
    """Наша правка не должна ломать синтаксис: снимаем комментарии и парсим."""
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text(КОНФИГ, encoding="utf-8")
    к = навыки(tmp_path, ["1c-queries", "1c-security", "1c-managed-forms"])

    запуск(к, конфиг)
    сырое = конфиг.read_text(encoding="utf-8")
    без = re.sub(r"//[^\n]*", "", сырое)
    без = re.sub(r"/\*.*?\*/", "", без, flags=re.S)
    d = json.loads(без)

    разрешения = d["permissions"]["skill"]
    assert разрешения["1c-queries"] == "allow"
    assert разрешения["1c-security"] == "allow"
    assert разрешения["1c-managed-forms"] == "allow"
    assert разрешения["*"] == "ask"


def test_повторный_запуск_ничего_не_меняет(tmp_path):
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text(КОНФИГ, encoding="utf-8")
    к = навыки(tmp_path, ["1c-queries"])

    запуск(к, конфиг)
    первый = конфиг.read_text(encoding="utf-8")
    р = запуск(к, конфиг)
    assert конфиг.read_text(encoding="utf-8") == первый
    assert "уже разрешены" in р.stdout


def test_запасная_копия_кладётся(tmp_path):
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text(КОНФИГ, encoding="utf-8")
    к = навыки(tmp_path, ["1c-queries"])

    запуск(к, конфиг)
    запас = tmp_path / "kilo.jsonc.bak"
    assert запас.exists()
    assert запас.read_text(encoding="utf-8") == КОНФИГ


def test_нет_конфига_это_предупреждение(tmp_path):
    к = навыки(tmp_path, ["1c-queries"])
    р = запуск(к, tmp_path / "нет-такого.jsonc")
    assert р.returncode == 0
    assert "предупреждение" in р.stdout


def test_нет_блока_skill_это_предупреждение(tmp_path):
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text('{\n  "permissions": { "bash": "ask" }\n}\n', encoding="utf-8")
    к = навыки(tmp_path, ["1c-queries"])

    р = запуск(к, конфиг)
    assert р.returncode == 0
    assert "предупреждение" in р.stdout
    # файл не тронут
    assert конфиг.read_text(encoding="utf-8") == '{\n  "permissions": { "bash": "ask" }\n}\n'


def test_проверить_ничего_не_пишет(tmp_path):
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text(КОНФИГ, encoding="utf-8")
    к = навыки(tmp_path, ["1c-queries"])

    р = запуск(к, конфиг, "--проверить")
    assert р.returncode == 0
    assert "1c-queries" in р.stdout
    assert конфиг.read_text(encoding="utf-8") == КОНФИГ
    assert not (tmp_path / "kilo.jsonc.bak").exists()


def test_пустой_блок_не_даёт_висячей_запятой(tmp_path):
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text('{\n  "permissions": {\n    "skill": {\n    }\n  }\n}\n',
                      encoding="utf-8")
    к = навыки(tmp_path, ["1c-queries", "1c-security"])

    запуск(к, конфиг)
    сырое = конфиг.read_text(encoding="utf-8")
    d = json.loads(сырое)  # без висячей запятой разбирается штатным json
    assert d["permissions"]["skill"] == {"1c-queries": "allow", "1c-security": "allow"}


def test_каталог_без_навыков_это_предупреждение(tmp_path):
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text(КОНФИГ, encoding="utf-8")
    пусто = tmp_path / "пусто"
    пусто.mkdir()

    р = запуск(str(пусто), конфиг)
    assert р.returncode == 0
    assert "предупреждение" in р.stdout
    assert конфиг.read_text(encoding="utf-8") == КОНФИГ


def test_подкаталог_без_skill_md_не_считается_навыком(tmp_path):
    """В каталоге навыков заводятся и служебные подкаталоги — они не навыки."""
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text(КОНФИГ, encoding="utf-8")
    к = навыки(tmp_path, ["1c-queries"])
    os.makedirs(os.path.join(к, "__pycache__"))

    запуск(к, конфиг)
    тело = блок(конфиг.read_text(encoding="utf-8"))
    assert "__pycache__" not in тело


КОНФИГ_ИМЯ_ВЫШЕ_ЗВЕЗДЫ = """\
{
  // Комментарий владельца, который нельзя потерять.
  "permissions": {
    "bash": "ask",
    "skill": {
      "developing-1c-configurations": "allow",
      "*": "ask",
      "writing-plans": "allow"
    },
    "websearch": "ask"
  },
  /* Блочный комментарий тоже остаётся. */
  "model": "opus"
}
"""

КОНФИГ_БЕЗ_ЗВЕЗДЫ = """\
{
  "permissions": {
    "skill": {
      "developing-1c-configurations": "allow"
    }
  }
}
"""


def позиция(текст, подстрока):
    и = текст.find(подстрока)
    assert и != -1, "%r не найдено в тексте" % подстрока
    return и


def test_звезда_есть_имён_нет_появляются_ниже_звезды(tmp_path):
    """Пустой (по нашим именам) блок со звёздочкой: новые имена — под ней."""
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text(КОНФИГ, encoding="utf-8")
    к = навыки(tmp_path, ["1c-queries", "1c-security"])

    р = запуск(к, конфиг)
    assert р.returncode == 0, р.stderr

    новый = конфиг.read_text(encoding="utf-8")
    п_звезды = позиция(новый, '"*": "ask"')
    п_queries = позиция(новый, '"1c-queries": "allow"')
    п_security = позиция(новый, '"1c-security": "allow"')
    assert п_queries > п_звезды, "1c-queries оказался не ниже звезды"
    assert п_security > п_звезды, "1c-security оказался не ниже звезды"


def test_звезда_есть_имя_выше_переставляется_вниз(tmp_path):
    """Имя есть, но только выше звезды - для Kilo это как отсутствующее.

    Инструмент обязан снять его сверху и завести свежую запись под звездой,
    а не оставить как есть (иначе "*": "ask" молча перебивает разрешение).
    """
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text(КОНФИГ_ИМЯ_ВЫШЕ_ЗВЕЗДЫ, encoding="utf-8")
    к = навыки(tmp_path, ["developing-1c-configurations", "writing-plans"])

    р = запуск(к, конфиг)
    assert р.returncode == 0, р.stderr

    новый = конфиг.read_text(encoding="utf-8")
    тело = блок(новый)
    # запись не задвоилась - старая (неверная) убрана, осталась одна
    assert тело.count('"developing-1c-configurations"') == 1
    # владелец не тронут
    assert "// Комментарий владельца, который нельзя потерять." in новый
    assert "/* Блочный комментарий тоже остаётся. */" in новый

    п_звезды = позиция(новый, '"*": "ask"')
    п_dev = позиция(новый, '"developing-1c-configurations": "allow"')
    assert п_dev > п_звезды, "developing-1c-configurations остался выше звезды"

    без = re.sub(r"//[^\n]*", "", новый)
    без = re.sub(r"/\*.*?\*/", "", без, flags=re.S)
    d = json.loads(без)
    разрешения = d["permissions"]["skill"]
    assert разрешения == {
        "*": "ask",
        "developing-1c-configurations": "allow",
        "writing-plans": "allow",
    }


def test_звезда_есть_имя_ниже_ничего_не_меняется(tmp_path):
    """Имя уже действует (стоит ниже звезды) - файл не переписывается."""
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text(КОНФИГ, encoding="utf-8")
    к = навыки(tmp_path, ["developing-1c-configurations"])

    р = запуск(к, конфиг)
    assert р.returncode == 0, р.stderr
    assert "уже разрешены" in р.stdout
    assert конфиг.read_text(encoding="utf-8") == КОНФИГ


def test_проверить_видит_имя_выше_звезды_и_не_молчит(tmp_path):
    """--проверить обязан назвать смещённое имя, а не соврать "уже разрешены"."""
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text(КОНФИГ_ИМЯ_ВЫШЕ_ЗВЕЗДЫ, encoding="utf-8")
    к = навыки(tmp_path, ["developing-1c-configurations", "writing-plans"])

    р = запуск(к, конфиг, "--проверить")
    assert р.returncode == 0, р.stderr
    assert "developing-1c-configurations" in р.stdout
    assert "уже разрешены" not in р.stdout
    # проверить ничего не пишет
    assert конфиг.read_text(encoding="utf-8") == КОНФИГ_ИМЯ_ВЫШЕ_ЗВЕЗДЫ


def test_нет_звезды_прежнее_поведение_вставки_в_начало(tmp_path):
    """Звёздочки нет вовсе - перебивать нечему, вставка идёт в начало блока."""
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text(КОНФИГ_БЕЗ_ЗВЕЗДЫ, encoding="utf-8")
    к = навыки(tmp_path, ["developing-1c-configurations", "1c-queries"])

    р = запуск(к, конфиг)
    assert р.returncode == 0, р.stderr

    новый = конфиг.read_text(encoding="utf-8")
    тело = блок(новый)
    assert тело.count('"developing-1c-configurations"') == 1

    п_queries = позиция(новый, '"1c-queries": "allow"')
    п_dev = позиция(новый, '"developing-1c-configurations": "allow"')
    assert п_queries < п_dev, "новое имя должно встать перед уже существующим"

    без = re.sub(r"//[^\n]*", "", новый)
    d = json.loads(без)
    assert d["permissions"]["skill"] == {
        "1c-queries": "allow",
        "developing-1c-configurations": "allow",
    }


def test_самопроверка_после_правки_смотрит_и_на_позицию(tmp_path):
    """Итог правки со смещённым именем обязан сам пройти новую проверку.

    Это не отдельная ветка кода, а побочный эффект того, что self-check
    внутри main() переиспользует ту же функцию оценки, что и вставка:
    после записи новый блок обязан показывать 0 отсутствующих и 0
    смещённых имён, иначе инструмент откажется и вернёт код 1.
    """
    конфиг = tmp_path / "kilo.jsonc"
    конфиг.write_text(КОНФИГ_ИМЯ_ВЫШЕ_ЗВЕЗДЫ, encoding="utf-8")
    к = навыки(tmp_path, ["developing-1c-configurations"])

    р = запуск(к, конфиг)
    assert р.returncode == 0, р.stderr
    assert р.stderr == ""


def test_установщик_зовёт_разрешение():
    """Правка бесполезна, если установщик её не вызывает."""
    установщик = os.path.join(КОРЕНЬ, "tools", "install-skills.ps1")
    текст = open(установщик, encoding="utf-8-sig").read()
    assert "allow-skills-in-kilo.py" in текст, (
        "install-skills.ps1 должен звать allow-skills-in-kilo.py — иначе "
        "навыки снова окажутся неразрешёнными и прогон Kilo покажет отказ "
        "набора вместо отказа списка разрешений")
