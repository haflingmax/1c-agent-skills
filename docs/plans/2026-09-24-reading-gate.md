# ВОРОТА-ЧТЕНИЯ: план реализации

> **Исполнителю:** ОБЯЗАТЕЛЬНЫЙ ПОДНАВЫК — `superpowers:subagent-driven-development`
> (рекомендуется) либо `superpowers:executing-plans`. Шаги помечены `- [ ]`.

**Цель.** Заставить набор прочитать себя там, где цена ошибки высока: прибор
отказывает до запуска, а не проза просит после.

**Архитектура.** Хук плагина `PreToolUse` перехватывает `Bash`, прогоняет
команды `1cv8` через существующий `check-1c-cli.py` и отказывает его же
выводом. Сам проверяльщик учится делить факты на три корзины: увиденное,
неизвестное и решение владельца. Там, где хуков нет (Kilo, Codex), правильный
путь делается короче пути по памяти — запускающая обёртка `run-1c.py`
проверяет, дожидается процесса и ставит диагноз зависанию.

**Инструменты.** Python 3 (стандартная библиотека), pytest, bash-шим для хука,
JSON-манифест хуков Claude Code.

**Спека.** `docs/specs/2026-09-24-reading-gate-design.md` — читать вместе
с этим планом.

## Общие ограничения

- **528 тестов обязаны оставаться зелёными.** Запуск: `python -m pytest -q`
  из корня репозитория. Полный прогон занимает 5–9 минут.
- **Кириллица в `.ps1` требует UTF-8 BOM**, иначе файл падает синтаксической
  ошибкой в неожиданном месте. В этом плане `.ps1` не заводится, но правило
  действует, если исполнитель решит его добавить.
- **Регулярные выражения не передаются через heredoc** — приезжают
  искажёнными молча. Писать файлом.
- **Версия двигается по `docs/releasing.md`:** любой коммит, меняющий
  `skills/`, обязан поднять `version` в `.claude-plugin/plugin.json`
  и `.codex-plugin/plugin.json` одним и тем же числом. Текущая — `0.7.0`.
- **Поле `hooks` в манифестах не заводится.** Каталог `hooks/`
  подхватывается Claude Code сам; у Codex поле `hooks` в рантайм
  не загружается, и объявлять его — воскрешать закрытый спор.
- **Чужие незакоммиченные правки не трогать:** в рабочей копии лежат
  `docs/releasing.md`, `tests/test_tools_write_guard.py`
  и `tools/sync-skills-to-codex-vscode.ps1` от другой сессии. Коммитить
  только свои пути, перечисленные в шагах.
- **Отказ обязан называть, на что прибор смотрел.** Молчаливый пропуск —
  дефект, который набор чинил трижды за 24.09.2026.

## На что смотреть ревьюеру

Пять классов входа, которые спека подразумевает, а задачи легко упустят.
Тест на каждый добавлен в задачу-владельца.

1. **Клиент-серверная база (`/S сервер/база`).** Файла на диске нет, и
   корзина «увидел сам» к ней неприменима. Проверка пути обязана
   молчать, а не отказывать. — Задача 1.
2. **Команда, лишь упоминающая `1cv8`** (`grep 1cv8 log.txt`). Сегодня
   даёт K017 и код 0; ворота обязаны её пропустить. Свойство есть — его
   нельзя сломать. — Задача 4.
3. **Кавычки внутри команды.** `/P"пароль с пробелом"` и пути в кавычках.
   Набор уже терял кавычки в PowerShell (`tools/native-arg.ps1`); разбор
   в хуке обязан их сохранять. — Задача 4.
4. **Python недоступен.** Ворота обязаны пропустить и сказать об этом,
   а не молча исчезнуть и не заблокировать всякую работу с `bash`. —
   Задача 4.
5. **Путь базы с пробелами и кириллицей.** `D:\1С базы\торговля` —
   проверка существования не должна ломаться на разборе. — Задача 1.

---

## Раскладка файлов

| Файл | Ответственность |
|---|---|
| `skills/1c-build-and-db/scripts/check-1c-cli.py` (правка) | разбор строки + три корзины фактов |
| `skills/1c-build-and-db/scripts/run-1c.py` (создать) | проверить, запустить, дождаться, поставить диагноз |
| `hooks/gate-1c.sh` (создать) | шим: найти python, передать payload, пропустить громко при его отсутствии |
| `hooks/gate-1c.py` (создать) | решение хука: разобрать payload, позвать проверяльщик, напечатать deny |
| `hooks/hooks.json` (создать) | регистрация `PreToolUse` на `Bash` |
| `tests/test_check_1c_cli.py` (правка) | регрессия корзин |
| `tests/test_run_1c.py` (создать) | обёртка на подставном исполняемом файле |
| `tests/test_gate_hook.py` (создать) | решение хука на готовых payload |

---

## Задача 1: проверяльщик видит базу и формат выгрузки

**Файлы:**
- Правка: `skills/1c-build-and-db/scripts/check-1c-cli.py`
- Тест: `tests/test_check_1c_cli.py`

**Интерфейсы:**
- Потребляет: `check(line, catalog) -> (problems, notes)` — существующая
  сигнатура, менять нельзя: на неё опираются 43 теста.
- Производит: два новых кода диагностики —
  `K_BASE_MISSING = "K018"` (ошибка) и `K_DUMP_FORMAT = "K019"` (внимание).

- [ ] **Шаг 1: написать падающий тест на отсутствующую файловую базу**

В `tests/test_check_1c_cli.py`, в конец файла:

```python
def test_file_base_missing_is_an_error(tmp_path):
    """K018: /F указывает в никуда. Это видно с диска, и молчать нельзя."""
    нет = tmp_path / "нет-такой-базы"
    line = ('1cv8 DESIGNER /F "%s" /LoadCfg new.cf /UpdateDBCfg -Dynamic- '
            '/DisableStartupDialogs /Out log.txt' % нет)
    assert any("K018" in p for p in problems(line))


def test_client_server_base_is_not_checked_on_disk():
    """Клиент-серверную базу на диске не ищут: /S — не путь."""
    line = ('1cv8 DESIGNER /S srv/trade /LoadCfg new.cf /UpdateDBCfg -Dynamic- '
            '/DisableStartupDialogs /Out log.txt')
    assert not any("K018" in p for p in problems(line))


def test_base_path_with_spaces_and_cyrillic(tmp_path):
    """Пробелы и кириллица в пути не ломают проверку существования."""
    база = tmp_path / "1С базы" / "торговля"
    база.mkdir(parents=True)
    (база / "1Cv8.1CD").write_bytes(b"x" * 10)
    line = ('1cv8 DESIGNER /F "%s" /LoadCfg new.cf /UpdateDBCfg -Dynamic- '
            '/DisableStartupDialogs /Out log.txt' % база)
    assert not any("K018" in p for p in problems(line))
```

- [ ] **Шаг 2: убедиться, что тесты падают**

Выполнить: `python -m pytest tests/test_check_1c_cli.py -k "K018 or base_path or client_server" -v`

Ожидается: `test_file_base_missing_is_an_error` — FAIL (K018 не найден,
кода ещё нет). Два остальных пройдут случайно: K018 не существует, значит
его нигде и нет. Это нормально — они сторожат от регрессии после шага 3.

- [ ] **Шаг 3: добавить код диагностики**

В `check-1c-cli.py`, в блок констант рядом с `K_FOREIGN_TOOL = "K017"`:

```python
K_BASE_MISSING = "K018"        # /F указывает на несуществующую базу
K_DUMP_FORMAT = "K019"         # версия формата выгрузки названа, релиз платформы неизвестен
```

- [ ] **Шаг 4: научить `check()` смотреть на диск**

В `check-1c-cli.py` добавить функцию перед `def check(`:

```python
def файловая_база(args):
    """Путь из /F, если он есть. /S — клиент-серверная, на диске её нет."""
    for i, a in enumerate(args):
        имя = a.strip('"')
        if имя.upper() == "/F" and i + 1 < len(args):
            return args[i + 1].strip('"')
        if слитный(имя, "/F"):
            return имя[2:].strip('"')
    return None


def слитный(арг, ключ):
    """Слитная форма: /Fd:/base. Регистр ключа платформе безразличен."""
    return (len(арг) > len(ключ)
            and арг[:len(ключ)].upper() == ключ.upper()
            and not арг[len(ключ)].isalpha())
```

Внутри `check()`, после существующих проверок ключей и перед `return`:

```python
    путь = файловая_база(args)
    существует = False
    if путь is not None:
        p = Path(путь)
        существует = p.is_dir() and (p / "1Cv8.1CD").is_file()
        if not существует:
            problems.append(
                "%s база по пути %s не найдена: нет ни каталога с 1Cv8.1CD, "
                "ни файла базы. Команда запустится и упадёт на открытии базы, "
                "а не на разборе строки" % (K_BASE_MISSING, путь))
```

`существует` вычисляется здесь один раз и переиспользуется в задаче 2:
корзины «знать не может» и «решение владельца» применимы только
к существующей базе.

- [ ] **Шаг 5: прогнать тесты задачи**

Выполнить: `python -m pytest tests/test_check_1c_cli.py -v`

Ожидается: PASS, все 46 тестов файла.

- [ ] **Шаг 6: добавить версию формата выгрузки как замечание**

Тест в `tests/test_check_1c_cli.py`:

```python
def test_dump_format_version_is_named(tmp_path):
    """K019: версию формата прибор видит, релиз платформы — нет. Называет обе."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "Configuration.xml").write_text(
        '<?xml version="1.0"?>\n<MetaDataObject version="2.18"/>',
        encoding="utf-8")
    line = ('1cv8 DESIGNER /F d:/base /LoadConfigFromFiles "%s" '
            '/UpdateDBCfg -Dynamic- /DisableStartupDialogs /Out log.txt' % src)
    assert any("K019" in n and "2.18" in n for n in notes(line))
```

Реализация — функция перед `check()`:

```python
def версия_формата(args):
    """version="…" из Configuration.xml выгрузки, если путь указан."""
    for i, a in enumerate(args):
        if a.strip('"').upper() == "/LOADCONFIGFROMFILES" and i + 1 < len(args):
            cfg = Path(args[i + 1].strip('"')) / "Configuration.xml"
            if cfg.is_file():
                m = re.search(r'version="([\d.]+)"',
                              cfg.read_text(encoding="utf-8", errors="replace")[:4000])
                return m.group(1) if m else None
    return None
```

И в `check()` рядом с проверкой базы:

```python
    вер = версия_формата(args)
    if вер:
        notes.append(
            "%s версия формата выгрузки %s. Релиз платформы прибору неизвестен: "
            "формат старше релиза загружается, новее — нет. Сверить с "
            "references/xml-dump-format.md" % (K_DUMP_FORMAT, вер))
```

- [ ] **Шаг 7: прогнать тесты и зафиксировать**

Выполнить: `python -m pytest tests/test_check_1c_cli.py -q`
Ожидается: PASS.

```bash
git add skills/1c-build-and-db/scripts/check-1c-cli.py tests/test_check_1c_cli.py
git commit -m "feat(check-1c-cli): корзина «увидел сам» — база на диске и версия формата"
```

---

## Задача 2: корзины «знать не может» и «решение владельца»

**Файлы:**
- Правка: `skills/1c-build-and-db/scripts/check-1c-cli.py`
- Тест: `tests/test_check_1c_cli.py`

**Интерфейсы:**
- Потребляет: `check(line, catalog)`, `файловая_база(args)` из задачи 1.
- Производит: `K_AUTH_UNKNOWN = "K020"`, `K_OWNER_DECISION = "K021"`
  и параметр командной строки `--ответ` со значениями
  `пользователей-нет`, `база-одноразовая`, `копия-сделана`
  (повторяемый: `--ответ пользователей-нет --ответ копия-сделана`).

- [ ] **Шаг 1: написать падающие тесты**

```python
def test_missing_auth_is_a_named_unknown(tmp_path):
    """K020: есть ли пользователи — прибор знать не может и обязан сказать."""
    база = tmp_path / "base"
    база.mkdir()
    (база / "1Cv8.1CD").write_bytes(b"x" * 10)
    line = ('1cv8 DESIGNER /F "%s" /LoadCfg new.cf /UpdateDBCfg -Dynamic- '
            '/DisableStartupDialogs /Out log.txt' % база)
    беда = [p for p in problems(line) if "K020" in p]
    assert беда, "молчание о неизвестном — тот самый дефект"
    assert "модальн" in беда[0], "отказ обязан объяснить, почему это выглядит как зависание"


def test_auth_present_closes_the_unknown(tmp_path):
    """С /N и /P вопрос закрыт."""
    база = tmp_path / "base"
    база.mkdir()
    (база / "1Cv8.1CD").write_bytes(b"x" * 10)
    line = ('1cv8 DESIGNER /F "%s" /N Администратор /P"" /LoadCfg new.cf '
            '/UpdateDBCfg -Dynamic- /DisableStartupDialogs /Out log.txt' % база)
    assert not any("K020" in p for p in problems(line))
```

- [ ] **Шаг 2: убедиться, что падают**

Выполнить: `python -m pytest tests/test_check_1c_cli.py -k "auth" -v`
Ожидается: `test_missing_auth_is_a_named_unknown` — FAIL.

- [ ] **Шаг 3: реализовать корзину «знать не может»**

Константы рядом с K019:

```python
K_AUTH_UNKNOWN = "K020"        # нет /N — есть ли пользователи, прибор не знает
K_OWNER_DECISION = "K021"      # непустая база: решение владельца не названо
```

Функция перед `check()`:

```python
def есть_аутентификация(args):
    for a in args:
        имя = a.strip('"')
        if имя.upper() == "/N" or слитный(имя, "/N"):
            return True
    return False
```

В `check()`:

```python
    if путь is not None and существует and not есть_аутентификация(args):
        problems.append(
            "%s команда без /N и /P. Есть ли в базе пользователи, прибор знать "
            "не может: список лежит внутри 1Cv8.1CD, и любой способ его "
            "прочитать сам требует аутентификации. Если пользователь есть хотя "
            "бы один, платформа покажет модальный диалог, до которого пакетный "
            "процесс не дотянется: процесс будет жив, вывод пуст, файл базы "
            "не изменится — это выглядит как зависание, а не как отказ. "
            "Добавить /N и /P либо подтвердить: --ответ пользователей-нет"
            % K_AUTH_UNKNOWN)
```

- [ ] **Шаг 4: прогнать тесты**

Выполнить: `python -m pytest tests/test_check_1c_cli.py -k "auth" -v`
Ожидается: PASS.

- [ ] **Шаг 5: написать падающий тест на решение владельца**

```python
def test_non_empty_base_demands_owner_decision(tmp_path):
    """K021: на непустой базе «рабочая или одноразовая» решает владелец."""
    база = tmp_path / "base"
    база.mkdir()
    (база / "1Cv8.1CD").write_bytes(b"x" * (2 * 1024 * 1024))
    line = ('1cv8 DESIGNER /F "%s" /N Админ /P"" /LoadCfg new.cf '
            '/UpdateDBCfg -Dynamic- /DisableStartupDialogs /Out log.txt' % база)
    беда = [p for p in problems(line) if "K021" in p]
    assert беда and "владельц" in беда[0]


def test_owner_answer_closes_the_decision(tmp_path):
    """--ответ база-одноразовая снимает вопрос."""
    база = tmp_path / "base"
    база.mkdir()
    (база / "1Cv8.1CD").write_bytes(b"x" * (2 * 1024 * 1024))
    line = ('1cv8 DESIGNER /F "%s" /N Админ /P"" /LoadCfg new.cf '
            '/UpdateDBCfg -Dynamic- /DisableStartupDialogs /Out log.txt' % база)
    assert not any("K021" in p
                   for p in mod.check(line, CATALOG, ответы={"база-одноразовая"})[0])
```

- [ ] **Шаг 6: расширить сигнатуру `check()` необязательным параметром**

Сигнатура меняется **только добавлением значения по умолчанию** — 43
существующих теста зовут `check(line, catalog)` и обязаны продолжать
работать:

```python
def check(line, catalog, ответы=frozenset()):
```

Логика в `check()`:

```python
    if путь is not None and существует:
        размер = (p / "1Cv8.1CD").stat().st_size
        необратимо = any(a.strip('"').upper() in
                         ("/LOADCFG", "/LOADCONFIGFROMFILES", "/UPDATEDBCFG",
                          "/RESTOREIB", "/ERASEDATA") for a in args)
        if размер > 0 and необратимо and not ({"база-одноразовая", "копия-сделана"} & set(ответы)):
            problems.append(
                "%s база непустая (%d байт). Рабочая она или одноразовая — "
                "решение владельца, а не догадка агента: от него зависит, "
                "нужна ли копия 1Cv8.1CD перед загрузкой. Ответить: "
                "--ответ база-одноразовая либо --ответ копия-сделана"
                % (K_OWNER_DECISION, размер))
```

И разбор параметра в `main()`, до сборки `line`:

```python
    ответы = set()
    остаток = []
    i = 0
    while i < len(argv):
        if argv[i] == "--ответ" and i + 1 < len(argv):
            ответы.add(argv[i + 1])
            i += 2
            continue
        остаток.append(argv[i])
        i += 1
    argv = остаток
```

и вызов `check(line, load_catalog(), ответы)`.

- [ ] **Шаг 7: прогнать весь файл тестов**

Выполнить: `python -m pytest tests/test_check_1c_cli.py -q`
Ожидается: PASS, 50 тестов.

- [ ] **Шаг 8: прогнать полный набор**

Выполнить: `python -m pytest -q`
Ожидается: PASS. Если упал `test_strengths.py` — смотреть, не разошлось ли
что-то в описаниях; правок описаний в этой задаче нет, значит дело в чём-то
другом, и это находка.

- [ ] **Шаг 9: зафиксировать**

```bash
git add skills/1c-build-and-db/scripts/check-1c-cli.py tests/test_check_1c_cli.py
git commit -m "feat(check-1c-cli): неизвестное называется, решение владельца не угадывается"
```

---

## Задача 3: запускающая обёртка

**Файлы:**
- Создать: `skills/1c-build-and-db/scripts/run-1c.py`
- Создать: `tests/test_run_1c.py`

**Интерфейсы:**
- Потребляет: `check-1c-cli.py` как модуль (`check`, `load_catalog`).
- Производит: `python run-1c.py [--ответ …] "<команда>"`; код возврата —
  `2` при отказе проверки, иначе код самой платформы. Функции для тестов:
  `запустить(команда, ответы, таймаут, исполняемый=None) -> (код, отчёт)`.

- [ ] **Шаг 1: написать тест на отказ до запуска**

`tests/test_run_1c.py`:

```python
"""Обёртка запуска 1cv8: проверяет, дожидается, ставит диагноз.

Настоящий 1cv8 в тестах не запускается. Вместо него подставной
исполняемый файл, умеющий ровно то, что надо проверить.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "1c-build-and-db" / "scripts" / "run-1c.py"

spec = importlib.util.spec_from_file_location("run_1c", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["run_1c"] = mod
spec.loader.exec_module(mod)


def test_refuses_to_run_a_command_that_fails_the_check(tmp_path):
    """Непрошедшая проверку команда не запускается вовсе."""
    код, отчёт = mod.запустить("1cv8 CONFIG /F d:/нет /LoadCfg a.cf",
                               ответы=set(), таймаут=5)
    assert код == 2
    assert "K002" in отчёт, "в отчёте обязан быть код отказа проверяльщика"
    assert "запуск не выполнялся" in отчёт
```

- [ ] **Шаг 2: убедиться, что падает**

Выполнить: `python -m pytest tests/test_run_1c.py -v`
Ожидается: FAIL — файла `run-1c.py` нет.

- [ ] **Шаг 3: написать обёртку**

`skills/1c-build-and-db/scripts/run-1c.py`:

```python
"""Запуск команды 1cv8 через проверку, с ожиданием и диагнозом зависания.

    python run-1c.py "1cv8 DESIGNER /F d:/base /N Админ /P\"\" /LoadCfg …"
    python run-1c.py --ответ база-одноразовая "…"

## Зачем

Голый запуск 1cv8 — худший из доступных способов, и это не мнение.
`1cv8.exe` собран как оконное приложение и возвращает управление немедленно
(references/load-configuration.md): запущенный обычным образом, он не даёт
ни журнала, ни кода возврата, и тихий отказ неотличим от успеха. Плюс
команду надо было проверить, а это отдельный шаг, который пропускают.

Обёртка делает оба шага одним и добавляет третий — диагноз зависанию.
Она не дисциплина, а выгода: короче и полезнее, чем запуск по памяти.
"""
import argparse
import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path

ЗДЕСЬ = Path(__file__).resolve().parent

if not os.environ.get("PYTHONIOENCODING"):
    for _поток in (sys.stdout, sys.stderr):
        try:
            _поток.reconfigure(encoding="utf-8", errors=_поток.errors)
        except (AttributeError, ValueError):
            pass


def _проверяльщик():
    сп = importlib.util.spec_from_file_location(
        "check_1c_cli_for_run", ЗДЕСЬ / "check-1c-cli.py")
    м = importlib.util.module_from_spec(сп)
    сп.loader.exec_module(м)
    return м


def запустить(команда, ответы=frozenset(), таймаут=3600, исполняемый=None):
    """(код возврата, отчёт). Код 2 — отказ проверки, запуск не состоялся."""
    м = _проверяльщик()
    беды, замечания = м.check(команда, м.load_catalog(), ответы)
    строки = [м.format_diag("ошибка", b) for b in беды]
    строки += [м.format_diag("внимание", z) for z in замечания]
    if беды:
        строки.append("запуск не выполнялся: команда не прошла проверку")
        return 2, "\n".join(строки)

    аргументы = м.split_args(команда)
    if исполняемый:
        аргументы = [исполняемый] + аргументы[1:]
    база = м.файловая_база(аргументы)
    было = _отпечаток(база)
    начало = time.time()
    процесс = subprocess.Popen(аргументы, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    try:
        вывод, _ = процесс.communicate(timeout=таймаут)
        код = процесс.returncode
    except subprocess.TimeoutExpired:
        процесс.kill()
        вывод, _ = процесс.communicate()
        строки.append(_диагноз(база, было, вывод))
        return 3, "\n".join(строки)
    строки.append("время: %.1f с, код возврата: %d" % (time.time() - начало, код))
    if вывод:
        строки.append(вывод.decode("utf-8", errors="replace").strip())
    return код, "\n".join(строки)


def _отпечаток(база):
    if not база:
        return None
    ф = Path(база) / "1Cv8.1CD"
    return (ф.stat().st_mtime, ф.stat().st_size) if ф.is_file() else None


def _диагноз(база, было, вывод):
    стало = _отпечаток(база)
    if not вывод and было is not None and было == стало:
        return ("[диагноз] процесс не завершился, вывод пуст, 1Cv8.1CD не менялся. "
                "Это не медленная операция: платформа показывает модальный диалог "
                "авторизации, до которого пакетный процесс не дотягивается. "
                "Не ждать дольше — добавить /N и /P либо запустить вручную.")
    return "[диагноз] истекло время ожидания; файл базы менялся, операция шла"


def main(argv=None):
    р = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    р.add_argument("--ответ", action="append", default=[],
                   help="пользователей-нет | база-одноразовая | копия-сделана")
    р.add_argument("--таймаут", type=int, default=3600)
    р.add_argument("команда")
    а = р.parse_args(argv)
    код, отчёт = запустить(а.команда, set(а.ответ), а.таймаут)
    print(отчёт)
    return код


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Шаг 4: прогнать тест отказа**

Выполнить: `python -m pytest tests/test_run_1c.py -v`
Ожидается: PASS.

- [ ] **Шаг 5: написать тест на диагноз зависания**

В `tests/test_run_1c.py`:

```python
def подставной(tmp_path, тело):
    """Исполняемый файл на python: делает ровно то, что нужно проверить."""
    ф = tmp_path / "1cv8-подставной.py"
    ф.write_text(тело, encoding="utf-8")
    return ф


def test_hang_with_untouched_base_is_diagnosed(tmp_path):
    """Процесс жив, вывод пуст, файл базы не менялся — это модальный диалог."""
    база = tmp_path / "base"
    база.mkdir()
    (база / "1Cv8.1CD").write_bytes(b"x" * 10)
    заглушка = подставной(tmp_path, "import time\ntime.sleep(30)\n")
    команда = ('1cv8 DESIGNER /F "%s" /N Админ /P"" /LoadCfg a.cf '
               '/UpdateDBCfg -Dynamic- /DisableStartupDialogs /Out log.txt'
               % база)
    код, отчёт = mod.запустить(команда, ответы={"база-одноразовая"}, таймаут=2,
                               исполняемый=sys.executable)
    assert код == 3
    assert "модальный диалог" in отчёт
```

**Замечание исполнителю:** подставной файл запускается как
`sys.executable <путь к .py>`, поэтому в `запустить()` подмена
исполняемого файла заменяет только `аргументы[0]`. Чтобы заглушка
получила свой скрипт, тест передаёт `исполняемый=sys.executable`,
а путь к заглушке подставляется в команду вместо `1cv8`. Если этого
окажется мало — расширить `запустить()` параметром `подмена_аргументов`,
но только после того, как тест покажет, что мало.

- [ ] **Шаг 6: прогнать и починить, пока не сойдётся**

Выполнить: `python -m pytest tests/test_run_1c.py -v`
Ожидается: PASS. Если подмена исполняемого файла не срабатывает —
править `запустить()` по замечанию шага 5, а не тест.

- [ ] **Шаг 7: прогнать полный набор и зафиксировать**

Выполнить: `python -m pytest -q`
Ожидается: PASS.

```bash
git add skills/1c-build-and-db/scripts/run-1c.py tests/test_run_1c.py
git commit -m "feat(build-and-db): обёртка запуска — проверка, ожидание, диагноз зависания"
```

---

## Задача 4: ворота — хук плагина

**Файлы:**
- Создать: `hooks/gate-1c.py`, `hooks/gate-1c.sh`, `hooks/hooks.json`
- Создать: `tests/test_gate_hook.py`

**Интерфейсы:**
- Потребляет: `check-1c-cli.py` по пути
  `${CLAUDE_PLUGIN_ROOT}/skills/1c-build-and-db/scripts/check-1c-cli.py`.
- Производит: `решение(payload_dict) -> dict | None`. `None` — пропустить
  молча; словарь — готовый JSON-ответ Claude Code.

- [ ] **Шаг 1: написать тесты решения хука**

`tests/test_gate_hook.py`:

```python
"""Решение ворот: что хук отвечает на готовый payload.

Хук — единственное место набора, работающее без участия модели. Поэтому
проверяется он не прогоном агента, а прямым вызовом на подготовленных
payload: так видно и отказ, и — важнее — что законное проходит.
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
    """Команда инцидента 28.08.2026 отклоняется до запуска."""
    ответ = mod.решение(payload(
        "1cv8 CONFIG /F D:/1C/base/trade /LoadConfigFromFiles D:/src /UpdateDBCfg"))
    assert ответ is not None
    вывод = ответ["hookSpecificOutput"]
    assert вывод["permissionDecision"] == "deny"
    assert "K002" in вывод["permissionDecisionReason"]


def test_mention_of_1cv8_is_not_a_launch():
    """grep 1cv8 log.txt — законная команда, ворота её пропускают."""
    assert mod.решение(payload("grep 1cv8 log.txt")) is None


def test_ordinary_command_passes_untouched():
    """Обычная работа воротами не задевается."""
    assert mod.решение(payload("git status --short")) is None


def test_quotes_inside_command_survive():
    """Кавычки внутри команды не теряются при разборе."""
    ответ = mod.решение(payload(
        '1cv8 DESIGNER /F "d:/нет такой базы" /P"пароль с пробелом" /LoadCfg a.cf'))
    assert ответ is not None
    assert "пароль с пробелом" not in ответ["hookSpecificOutput"]["permissionDecisionReason"], \
        "пароль не должен попадать в текст отказа"


def test_other_tools_are_ignored():
    """Хук стоит на Bash; Read и Write его не касаются."""
    assert mod.решение(payload("что угодно", инструмент="Read")) is None
```

- [ ] **Шаг 2: убедиться, что падают**

Выполнить: `python -m pytest tests/test_gate_hook.py -v`
Ожидается: FAIL — `hooks/gate-1c.py` не существует.

- [ ] **Шаг 3: написать решение хука**

`hooks/gate-1c.py`:

```python
"""Ворота: команда 1cv8 не запускается, не пройдя проверку.

## Зачем

Набор читают по диагонали. Агент инцидента 28.08.2026 остановился на
описании навыка, не открыл ни тела, ни справочников, не запустил
проверяльщик — и полтора часа бился в модальный диалог, которого не видел.
Проверяльщик отказал бы на первой же его команде (код 1, «CONFIG не режим
запуска»). Не хватало не знания, а принуждения.

Ворота работают, даже если модель не открывала навык вообще.

## Граница

Арбитром «похоже ли это на запуск 1cv8» служит сам проверяльщик, а не
регулярка здесь. Подбор по имени в этом наборе — известная ловушка:
`grep 1cv8 log.txt` регулярка поймает, и ворота начнут мешать законному.
Проверяльщик на такую команду отвечает кодом K017 и кодом возврата 0.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

КОРЕНЬ = Path(os.environ.get("CLAUDE_PLUGIN_ROOT",
                             Path(__file__).resolve().parent.parent))
ПРОВЕРЯЛЬЩИК = КОРЕНЬ / "skills" / "1c-build-and-db" / "scripts" / "check-1c-cli.py"


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
        "Команда 1cv8 не прошла проверку и не запущена.\n\n%s\n"
        "Это ворота набора 1c-agent-skills: ключи командной строки 1С "
        "не пишутся по памяти — их 140, и выдуманный выглядит правдоподобно. "
        "Разбор — в навыке 1c-build-and-db (SKILL.md и "
        "references/load-configuration.md). Запускать через "
        "scripts/run-1c.py: он проверяет, дожидается процесса и ставит "
        "диагноз зависанию." % готово.stdout.strip())
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": причина,
        "additionalContext": причина,
    }}


def main():
    try:
        payload = json.loads(os.environ.get("HOOK_PAYLOAD") or sys.stdin.read() or "{}")
        if isinstance(payload, dict):
            ответ = решение(payload)
            if ответ is not None:
                print(json.dumps(ответ, ensure_ascii=False, separators=(",", ":")))
    except Exception:
        # Ворота не имеют права ломать работу: любая своя беда — пропуск.
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Шаг 4: прогнать тесты решения**

Выполнить: `python -m pytest tests/test_gate_hook.py -v`
Ожидается: PASS, пять тестов.

- [ ] **Шаг 5: написать шим и манифест хуков**

`hooks/gate-1c.sh`:

```bash
#!/usr/bin/env bash
# Шим ворот: найти python, передать payload, пропустить громко без него.
#
# Отсутствие интерпретатора не имеет права блокировать всякую работу с bash,
# но и молчать о нём нельзя: молчаливый пропуск — тот самый класс дефекта,
# который набор чинил трижды 24.09.2026 (docs/debt.md, раздел 5).
payload="$(cat)"

for кандидат in python3 python py; do
  if command -v "$кандидат" >/dev/null 2>&1; then
    HOOK_PAYLOAD="$payload" "$кандидат" "${CLAUDE_PLUGIN_ROOT}/hooks/gate-1c.py" || true
    exit 0
  fi
done

if printf '%s' "$payload" | grep -qi '1cv8'; then
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"Ворота 1c-agent-skills пропустили команду не глядя: python не найден в PATH, проверить командную строку 1cv8 нечем. Это не одобрение команды."}}'
fi
exit 0
```

`hooks/hooks.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/gate-1c.sh\"",
            "shell": "bash",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

- [ ] **Шаг 6: проверить шим вручную на обеих ветках**

Выполнить из корня репозитория:

```bash
CLAUDE_PLUGIN_ROOT="$PWD" bash hooks/gate-1c.sh <<'EOF'
{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"1cv8 CONFIG /F d:/base /LoadCfg a.cf"}}
EOF
```

Ожидается: одна строка JSON с `"permissionDecision":"deny"` и кодом K002
внутри причины.

```bash
CLAUDE_PLUGIN_ROOT="$PWD" bash hooks/gate-1c.sh <<'EOF'
{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git status"}}
EOF
```

Ожидается: пустой вывод, код возврата 0.

- [ ] **Шаг 7: прогнать полный набор и зафиксировать**

Выполнить: `python -m pytest -q`
Ожидается: PASS.

```bash
git add hooks/ tests/test_gate_hook.py
git commit -m "feat(hooks): ворота PreToolUse — команда 1cv8 не запускается без проверки"
```

---

## Задача 5: правки навыков и учёт

**Файлы:**
- Правка: `skills/1c-build-and-db/SKILL.md`
- Правка: `skills/developing-1c-configurations/SKILL.md`
- Правка: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`
- Правка: `CHANGELOG.md`, `docs/debt.md`
- Правка: `skills/developing-1c-configurations/references/architecture.md`

**Интерфейсы:**
- Потребляет: `run-1c.py` из задачи 3, ворота из задачи 4.
- Производит: версию `0.8.0` в обоих манифестах.

- [ ] **Шаг 1: перенести правило на первую строку тела**

В `skills/1c-build-and-db/SKILL.md` сразу под заголовком `# ...`, **до**
любого другого раздела, вставить:

```markdown
**Ключи командной строки 1С не пишутся по памяти.** Их 140, они похожи друг
на друга, и выдуманный ключ выглядит правдоподобно. Запускай через обёртку —
она проверит команду, дождётся процесса и объяснит зависание:

```
python scripts/run-1c.py "1cv8 DESIGNER /F d:/base /N Админ /P\"\" /LoadCfg new.cf /UpdateDBCfg -Dynamic- /DisableStartupDialogs /Out log.txt"
```

В Claude Code это не пожелание: запуск `1cv8` мимо проверки отклоняется
воротами плагина до выполнения.
```

Существующий раздел с тем же правилом **удалить**, чтобы оно не стояло
в файле дважды: одно правило — одно место.

- [ ] **Шаг 2: проверить бюджет тела**

Выполнить: `python tools/check-skills.py`
Ожидается: `нарушений: 0`. Предупреждение о превышении ориентира 5000
токенов у `1c-build-and-db` — повод сжать прозу в том же файле, а не
основание бросить шаг.

- [ ] **Шаг 3: добавить повод в описание**

В том же файле, во фронтматтере, в конец `description`:

```
 Описание — только триггер: правила лежат в теле навыка и в references/, и без них команда не запустится.
```

- [ ] **Шаг 4: пересчитать бюджет каталога**

Выполнить:

```bash
python - <<'EOF'
import re
from pathlib import Path
всего = 0
for p in sorted(Path("skills").glob("*/SKILL.md")):
    t = p.read_text(encoding="utf-8")
    m = re.search(r"^description:\s*(.+?)\n(?=\w+:|---)", t, re.S | re.M)
    всего += len(" ".join(m.group(1).split())) + len(p.parent.name)
print(всего, round(всего / 8000 * 100), "%")
EOF
```

Ожидается: около 7370 знаков, 92 %. Если вышло больше 7600 — описание
сокращать, а не бюджет.

- [ ] **Шаг 5: обновить замер в архитектуре**

В `skills/developing-1c-configurations/references/architecture.md`
в таблице «Навык | Знаков в описании» заменить строку
`| `1c-build-and-db` | <старое> |` на новое число, и обновить итог
в абзаце ниже. Это сторожит тест
`tests/test_strengths.py::test_catalogue_budget_numbers_are_current`.

- [ ] **Шаг 6: назвать обёртку в ядре**

В `skills/developing-1c-configurations/SKILL.md`, «Порядок работы над
задачей», пункт 4: заменить упоминание `scripts/check-1c-cli.py`
на `scripts/run-1c.py`, сохранив всю остальную формулировку пункта —
в ней записано правило о недостижимом файле проверяльщика, и оно остаётся
верным.

- [ ] **Шаг 7: поднять версию**

В `.claude-plugin/plugin.json` и `.codex-plugin/plugin.json`:
`"version": "0.7.0"` → `"version": "0.8.0"`.

Выполнить: `python tools/check-manifests.py`
Ожидается: `нарушений: 0`.

- [ ] **Шаг 8: записать в CHANGELOG и долг**

В `CHANGELOG.md` новым разделом сверху — `## 0.8.0 — <дата>` с разделами
«Добавлено» (ворота, обёртка, три корзины) и «Исправлено» (правило
переехало на первую строку тела).

В `docs/debt.md`, раздел 5 «Долг процесса и приборов», добавить пункт:
ворота работают только в Claude Code; в Kilo и Codex принуждения нет,
рычаг `AGENTS.md` не взят и ждёт замера.

- [ ] **Шаг 9: прогнать полный набор и зафиксировать**

Выполнить: `python -m pytest -q`
Ожидается: PASS.

```bash
git add skills/1c-build-and-db/SKILL.md skills/developing-1c-configurations/SKILL.md \
        skills/developing-1c-configurations/references/architecture.md \
        .claude-plugin/plugin.json .codex-plugin/plugin.json CHANGELOG.md docs/debt.md
git commit -m "feat(skills): правило на первой строке, обёртка как единственный путь, 0.8.0"
```

---

## Задача 6: живая проверка и свидетельство

**Файлы:**
- Создать: `docs/evidence/2026-09-24-reading-gate-live.md`

**Интерфейсы:**
- Потребляет: всё, сделанное в задачах 1–5.
- Производит: свидетельство с тремя исходами по прежней мере.

- [ ] **Шаг 1: поставить свежие навыки во все три среды**

Выполнить: `powershell -File tools/install-skills.ps1`
Ожидается: три строки «поставлено в …». Сверка копий обязательна —
`tools/run-prompt.ps1` откажется работать на устаревшей.

- [ ] **Шаг 2: прогнать задачу инцидента в трёх средах**

Промпт (подсказок не давать): `Загрузи конфигурацию в базу данных.`

Выполнить для каждой среды:

```powershell
powershell -File tools/run-prompt.ps1 -Env claude -Prompt 'Загрузи конфигурацию в базу данных.' -Dir d:\github.com\haflingmax\trade
```

и то же с `-Env kilo`, `-Env codex`.

**После каждого прогона удалить `run.log` из репозитория `trade`** — он
пишется в рабочий каталог и репозиторий не наш.

- [ ] **Шаг 3: снять три критерия успеха**

По журналам каждого прогона ответить на три вопроса и записать ответы:

1. в Claude Code — была ли попытка запустить `1cv8` мимо проверки и
   отклонили ли её ворота;
2. в Kilo и Codex — выбрана ли обёртка `run-1c.py` (искать её имя
   в журнале);
3. **сколько отказов ворот получили законные команды** — искать в журналах
   `permissionDecision` рядом с командами без `1cv8`. Ожидается ноль.

- [ ] **Шаг 4: написать свидетельство**

`docs/evidence/2026-09-24-reading-gate-live.md` по образцу
`docs/evidence/2026-09-24-db-deepening-live-check.md`: таблица «среда ×
критерий», исходы трёхисходной мерой, раздел находок и раздел «что
подтвердилось попутно».

Если хотя бы один критерий не выполнен — записать это как результат,
а не как повод переписывать критерий.

- [ ] **Шаг 5: зафиксировать**

```bash
git add docs/evidence/2026-09-24-reading-gate-live.md
git commit -m "docs(evidence): живая проверка ворот в трёх средах"
```

---

## Самопроверка плана

**Покрытие спеки.** Раздел 1 спеки (ворота) — задача 4; три корзины —
задачи 1 и 2; раздел 2 (обёртка) — задача 3; раздел 3 (правки навыков) —
задача 5; раздел 4 (чем проверяем) — модульные тесты внутри задач 1–4
и живая проверка в задаче 6. Решение «python недоступен — пропускать
громко» реализовано в шиме задачи 4, шаг 5. Решение «ворота только
на 1cv8» выполняется само: арбитром служит проверяльщик, который отвечает
K017 на чужой инструмент.

**Заглушек нет.** Каждый шаг несёт код либо точную команду с ожидаемым
результатом.

**Согласованность имён.** `check(line, catalog, ответы=frozenset())` —
задача 2, шаг 6; используется в задаче 3 как `м.check(команда,
м.load_catalog(), ответы)`. `файловая_база(args)` — задача 1, шаг 4;
используется в задаче 3. `решение(payload)` — задача 4, шаг 3;
используется в тестах того же шага. `запустить(команда, ответы, таймаут,
исполняемый)` — задача 3, шаг 3; вызывается в тестах шагов 1 и 5.

**Классы входа из «На что смотреть ревьюеру»** закрыты тестами:
клиент-серверная база — задача 1, шаг 1; упоминание `1cv8` без запуска —
задача 4, шаг 1; кавычки — задача 4, шаг 1; отсутствие python — задача 4,
шаг 5 плюс ручная проверка шага 6; пробелы и кириллица в пути — задача 1,
шаг 1.
