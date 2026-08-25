"""Регресс сильных сторон набора.

Каждый тест соответствует свойству, отмеченному ревью как ценное. Смысл —
не дать доработке сломать то, что уже сделано верно. Источник формулировок:
docs/reviews/2026-08-23-core-review.md, раздел «Сильные стороны» (43 пункта).

Сюда попали пункты, чьё ЯДРО — факт о файлах репозитория. Соответствие
«какая из 43 сторон каким тестом сторожится» расписано поимённо в
docs/reviews/2026-08-23-strengths-manual.md и сторожится там же тестом
test_strengths_mapping_is_complete_and_names_real_tests: 20 сторон под
тестом целиком, 9 — тестом и человеком (остаток назван в строке), 14 —
только человеком.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = sorted((ROOT / "skills").rglob("SKILL.md"))


def _frontmatter_and_body(md):
    text = md.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    assert m, "нет фронтматтера в %s" % md
    return m.group(1), text[m.end():]


def test_names_within_limits():
    """Имена: только строчная латиница, цифры и дефис, не длиннее 64 знаков."""
    for md in SKILLS:
        name = re.search(r"^name:\s*(.+)$", md.read_text(encoding="utf-8"), re.M).group(1).strip()
        assert re.fullmatch(r"[a-z0-9-]+", name), name
        assert len(name) <= 64, name
        assert "claude" not in name and "anthropic" not in name, name


def test_references_are_one_level():
    """Справочные файлы не ссылаются дальше: цепочек SKILL.md → файл → файл нет."""
    for ref in sorted((ROOT / "skills").rglob("references/*.md")):
        links = re.findall(r"\]\(([^)]+\.md)\)", ref.read_text(encoding="utf-8"))
        assert not links, "%s ссылается дальше: %s" % (ref, links)


def test_plugin_layout():
    """.claude-plugin несёт только манифесты, skills лежит в корне."""
    assert (ROOT / "skills").is_dir()
    inside = {p.name for p in (ROOT / ".claude-plugin").iterdir()}
    assert inside <= {"plugin.json", "marketplace.json"}, inside


def test_marketplace_source_is_repo_root():
    """source: './' — маркет и плагин это один репозиторий."""
    mk = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert mk["plugins"][0]["source"] == "./"


def test_no_hard_dependency_on_other_plugins():
    """superpowers объявлен рекомендацией, а не зависимостью."""
    m = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert "dependencies" not in m, (
        "жёсткая зависимость выключит весь набор при отсутствии плагина")


# --- Дальше — пункты, добавленные сверх пяти стартовых из брифа ------------


def test_description_formula_third_person():
    """Описание построено как «что делает + когда применять», в третьем лице
    (дословно предписанная Anthropic формула; та же формулировка описания —
    и пункт «description переписан по последствию для ответа»)."""
    when_to_use = re.compile(r"применяется,?\s+когда", re.I)
    first_or_second_person = re.compile(
        r"\b(используй|используйте|примени|применяй|запусти|запускай|создай|"
        r"проверь|сделай|ты\s|вы\s|вам\b|тебе\b)\b", re.I)
    for md in SKILLS:
        fm, _ = _frontmatter_and_body(md)
        desc = re.search(r"^description:\s*(.+)$", fm, re.M).group(1).strip()
        assert when_to_use.search(desc), "%s: нет «применяется, когда» в описании" % md
        assert not first_or_second_person.search(desc), (
            "%s: описание не в третьем лице" % md)


def test_description_and_body_within_anthropic_limits():
    """Все замеренные ограничения — с запасом: description ≤ 1024 знаков,
    тело ≤ 500 строк (пределы спецификации Anthropic, не наших порогов)."""
    for md in SKILLS:
        fm, body = _frontmatter_and_body(md)
        desc = re.search(r"^description:\s*(.+)$", fm, re.M).group(1).strip()
        assert len(desc) <= 1024, (md, len(desc))
        assert body.count("\n") <= 500, (md, body.count("\n"))


def test_bundled_data_not_loaded_as_context():
    """31 КБ состава ключей — данные для скрипта, а не контекст для чтения:
    cli-keys.json существует как объёмный файл и не подключён markdown-
    ссылкой ни из одного SKILL.md или references/*.md."""
    data_file = ROOT / "skills" / "1c-build-and-db" / "scripts" / "cli-keys.json"
    assert data_file.exists()
    assert data_file.stat().st_size > 10_000, "каталог ключей подозрительно мал"
    for md in sorted((ROOT / "skills").rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        assert "](scripts/cli-keys.json)" not in text and "](../scripts/cli-keys.json)" not in text, (
            "%s подключает данные скрипта как читаемый reference" % md)


def test_frontmatter_has_only_name_and_description():
    """Codex: «Do not include any other fields in YAML frontmatter» — во
    фронтматтере обоих навыков ровно name и description, без лишнего."""
    for md in SKILLS:
        fm, _ = _frontmatter_and_body(md)
        keys = set(re.findall(r"^([A-Za-z_-]+):", fm, re.M))
        assert keys == {"name", "description"}, (md, keys)


def test_no_readme_or_changelog_inside_skill_folders():
    """Codex прямо запрещает README/CHANGELOG и прочую обвязку внутри
    папки навыка — раскладка должна оставаться SKILL.md + references/ + scripts/."""
    forbidden = re.compile(r"^(readme|changelog|installation_guide|quick_reference)", re.I)
    for skill_dir in (ROOT / "skills").iterdir():
        if not skill_dir.is_dir():
            continue
        for p in skill_dir.rglob("*"):
            if p.is_file() and forbidden.match(p.name):
                raise AssertionError("лишний файл обвязки: %s" % p)


def test_codex_manifest_skills_and_interface_complete():
    """Поле skills в единственной принимаемой форме («./skills/»), блок
    interface заполнен всеми обязательными полями плюс defaultPrompt —
    ключевой контракт каталога Codex."""
    m = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert m.get("skills") == "./skills/"
    interface = m.get("interface", {})
    for field in ("displayName", "shortDescription", "longDescription",
                  "developerName", "category"):
        assert interface.get(field), "interface.%s пуст или отсутствует" % field
    assert interface.get("defaultPrompt"), "нет defaultPrompt"


def test_checkers_exist():
    """Набор несёт автоматических проверяльщиков с ненулевым кодом при
    нарушении — не голая документация. Само поведение (код 0/1) проверяют
    их собственные тесты и Шаг 11 приёмки; здесь фиксируется, что они не
    потерялись при доработке."""
    for name in ("check-skills.py", "check-sources.py", "check-manifests.py"):
        assert (ROOT / "tools" / name).is_file(), "нет tools/%s" % name


def test_no_backslash_paths_or_env_var_refs():
    """Внутри тел навыков пути — прямыми косыми, даже под Windows, и без
    привязки к переменным конкретной среды (${CLAUDE_*} и т.п.): проверено
    напрямую по файлам, а не через правило check-skills.py, которое может
    измениться."""
    backslash_path = re.compile(r"[A-Za-z_}\]]\\[A-Za-z_{]")
    env_var = re.compile(r"\$\{?(CLAUDE|KILO|CURSOR)_[A-Z_]*\}?")
    for md in SKILLS:
        text = md.read_text(encoding="utf-8")
        assert not backslash_path.search(text), "%s: обратные косые в пути" % md
        assert not env_var.search(text), "%s: привязка к переменной среды" % md


def test_evidence_table_present():
    """«Отчёт инструмента не считается доказательством» проведено явной
    таблицей «Утверждение | Чем доказывается» в 1c-build-and-db/SKILL.md —
    доменный двойник verification-before-completion."""
    text = (ROOT / "skills" / "1c-build-and-db" / "SKILL.md").read_text(encoding="utf-8")
    assert re.search(r"\|\s*Утверждение\s*\|\s*Чем доказывается\s*\|", text), (
        "таблица «Утверждение | Чем доказывается» потерялась")


def test_precondition_recognition_questions_present():
    """Признак предпосылки вместо закрытого списка вопросов.

    I-5: тест был засчитан сразу за три сильные стороны, а проверял два
    слова. Теперь он отвечает ровно за одну — [лучшие-наборы] «Признак
    предпосылки вместо чек-листа вопросов» — и проверяет её целиком: обе
    формулировки признака И оговорку «перечень открыт с обоих концов»,
    которая и делает перечень признаком, а не списком. Соседние стороны
    из блоков [ошибки] и [другие-экосистемы] проверяет тест ниже.
    """
    text = (ROOT / "skills" / "developing-1c-configurations" / "SKILL.md").read_text(encoding="utf-8")
    assert "Развилка?" in text, "вопрос «Развилка?» потерялся"
    assert "Своя починка?" in text, "вопрос «Своя починка?» потерялся"
    assert "Перечень открыт с обоих концов" in text, (
        "оговорка «перечень открыт с обоих концов» потерялась — без неё "
        "признак превращается в закрытый список")


def test_precondition_pair_working_or_disposable_base():
    """Пара «рабочая база / одноразовая» и все её исходы.

    I-5: сильная сторона из блока [ошибки] — «признак предпосылки вместо
    закрытого перечня вопросов (пара «рабочая база / одноразовая»)» — была
    засчитана за тест, который проверял совсем другую пару. Задача 4
    переписала именно этот раздел ядра: два исхода стали тремя. Сторожим
    все три, а не два слова.
    """
    core = (ROOT / "skills" / "developing-1c-configurations" / "SKILL.md").read_text(encoding="utf-8")
    build = (ROOT / "skills" / "1c-build-and-db" / "SKILL.md").read_text(encoding="utf-8")
    for text, who in ((core, "ядро"), (build, "1c-build-and-db")):
        assert "рабочая база" in text or "база **рабочая**" in text, (
            "%s: признак «рабочая база» потерялся" % who)
        assert "одноразов" in text, "%s: признак «одноразовая» потерялся" % who
    # Три исхода задачи 4: спросить, сказать вслух и работать, пропустить шаг.
    assert "копия **уже сделана**" in core, "третий исход (копия уже есть) потерялся"
    assert "Пропусти шаг и отметь пропуск" in core, "исход «пропустить шаг» потерялся"
    assert "все три исхода" in core, (
        "правило «ответ закрывает все три исхода разом» потерялось")


def test_deterministic_script_over_generated_code():
    """Детерминированная сверка состава ключей вместо генерации кода на лету.

    I-5: сильная сторона [anthropic] «Скрипт check-1c-cli.py — образцовое
    применение „Prefer scripts for deterministic operations"» лежала в
    ручном списке с основанием «сам скрипт вне файлов этой задачи». Задача 3
    этот скрипт переписала (+327 строк) — основание перестало быть верным.
    Фактическая половина стороны машинно проверяема: каталог из полутора
    сотен ключей на месте, а навык предписывает ЗАПУСК скрипта, не чтение
    каталога. Оценка «образцовое применение» остаётся суждением и остаётся
    в ручном списке.
    """
    catalog = json.loads(
        (ROOT / "skills" / "1c-build-and-db" / "scripts" / "cli-keys.json")
        .read_text(encoding="utf-8"))
    assert len(catalog["ключи"]) >= 140, len(catalog["ключи"])
    body = (ROOT / "skills" / "1c-build-and-db" / "SKILL.md").read_text(encoding="utf-8")
    assert "python scripts/check-1c-cli.py" in body, (
        "навык больше не предписывает запуск проверяльщика")


def test_blocking_rules_carry_their_own_proof():
    """«Запрещай только доказанное»: у каждой блокировки — свой прогон.

    I-5: две сильные стороны ([ошибки] «Замер вместо мнения» и
    [лучшие-наборы] «Правило „запрещай только доказанное"») лежали в ручном
    списке с основанием «check-1c-cli.py и его доказательная база вне файлов
    этой задачи». Задача 3 переписала и скрипт, и базу. Ядро обеих сторон
    проверяемо чтением: список блокирующих ключей мал, каждый несёт ссылку
    на прогон, и каждый назван в файле доказательств.
    """
    spec = importlib.util.spec_from_file_location(
        "check_1c_cli_strengths",
        ROOT / "skills" / "1c-build-and-db" / "scripts" / "check-1c-cli.py")
    cli = importlib.util.module_from_spec(spec)
    sys.modules["check_1c_cli_strengths"] = cli
    spec.loader.exec_module(cli)

    evidence = (ROOT / "docs" / "evidence" / "2026-08-22-blocking-rules.md").read_text(
        encoding="utf-8")
    assert cli.PROVEN_TAIL_MISPARSE, "список доказанных блокировок опустел"
    for key, proof in cli.PROVEN_TAIL_MISPARSE.items():
        assert "запуском" in proof, "%s: блокировка без ссылки на прогон" % key
        assert key in evidence, (
            "%s блокирует, но в docs/evidence/2026-08-22-blocking-rules.md "
            "не назван" % key)


def test_regression_tests_are_traceable_to_defects():
    """Прослеживаемость «дефект → тест», которой нет у superpowers.

    I-5: сторона была засчитана в ручной список дважды с основанием
    «tests/test_check_1c_cli.py — уже существующий файл вне области этой
    задачи», а задачи 2–3 добавили в него +347 строк. Сторожим не долю
    (она ломалась бы от безобидного переименования, и это возражение было
    верным), а сам факт: заявление о прослеживаемости стоит в файле, и
    номера дефектов в нём действительно есть.
    """
    text = (ROOT / "tests" / "test_check_1c_cli.py").read_text(encoding="utf-8")
    assert "соответствует дефекту" in text, (
        "заявление о прослеживаемости «дефект → тест» потерялось")
    named = re.findall(r"^def (test_d\d+_\w+)", text, re.M)
    assert len(named) >= 7, named
    referenced = set(re.findall(r"[ДН]-\d\d", text))
    assert len(referenced) >= 5, referenced


def test_strengths_mapping_is_complete_and_names_real_tests():
    """I-5: соответствие «сильная сторона → тест» расписано, а не выводится вычитанием.

    Раньше в ручном списке стояло «22 из 43 покрыты, 21 здесь», а какой тест
    за какую сторону отвечает — нигде: соответствие 22 ↔ 15 тестов
    приходилось восстанавливать вычитанием. Теперь оно расписано таблицей,
    и таблица сторожится: ровно 43 строки, разбивка по блокам как в
    документе находок, и каждый названный тест существует.
    """
    doc = (ROOT / "docs" / "reviews" / "2026-08-23-strengths-manual.md").read_text(
        encoding="utf-8")
    rows = re.findall(r"^\| ([ACELD]\d+) \| (.+?) \| (.+?) \|$", doc, re.M)
    assert len(rows) == 43, "в документе находок ровно 43 сильные стороны, в таблице %d" % len(rows)

    ids = [r[0] for r in rows]
    assert len(set(ids)) == 43, "повторяющиеся номера: %s" % [
        i for i in ids if ids.count(i) > 1]
    blocks = {}
    for i in ids:
        blocks[i[0]] = blocks.get(i[0], 0) + 1
    assert blocks == {"A": 10, "C": 8, "E": 8, "L": 8, "D": 9}, blocks

    named = set()
    for _, _, how in rows:
        named |= set(re.findall(r"`(test_\w+)`", how))
    existing = set()
    for f in sorted((ROOT / "tests").glob("*.py")):
        existing |= set(re.findall(r"^def (test_\w+)", f.read_text(encoding="utf-8"), re.M))
    assert named <= existing, "таблица ссылается на несуществующие тесты: %s" % sorted(
        named - existing)


def test_core_names_collected_skills_inline():
    """I-7: состав набора агент узнаёт из самого навыка, а не из чужой среды.

    Ядро отсылало за составом «в README или вывод `/plugin`». `/plugin` —
    команда Claude Code, в Kilo и Codex её нет; README лежит вне `skills/`,
    а манифест Codex указывает только на `./skills/`. Это ровно тот дефект,
    от которого набор лечится в трёх других местах: правило «нет привязки к
    одной среде» в `references/architecture.md`, механический запрет
    `${CLAUDE_*}` в `check-skills.py`, разбор опровергнутой О-17 про знание,
    положенное туда, куда работающий агент не заглянет.

    Теперь состав назван строкой в самом навыке — и строка обязана совпадать
    с содержимым `skills/`, иначе она устареет молча.
    """
    core = ROOT / "skills" / "developing-1c-configurations" / "SKILL.md"
    text = core.read_text(encoding="utf-8")

    assert "/plugin" not in text, (
        "ядро снова отсылает к команде, которой нет в Kilo и Codex")

    m = re.search(r"\*\*Собран(?:ы)? сейчас [^*]*?:([^*]+)\*\*", text)
    assert m, "в ядре нет строки «Собран сейчас …» с составом набора"
    named = set(re.findall(r"`([a-z0-9-]+)`", m.group(1)))

    collected = {d.name for d in (ROOT / "skills").iterdir()
                 if d.is_dir() and (d / "SKILL.md").exists()}
    collected.discard("developing-1c-configurations")
    assert named == collected, (
        "строка состава в ядре разошлась с skills/: названо %s, лежит %s"
        % (sorted(named), sorted(collected)))


def test_readme_marks_unverified_install_paths():
    """M-8: README обещал пути, которых никто не пробовал.

    Отчёт задачи 4 честно писал, что прогона по Copilot, Gemini и Cursor не
    было, — а таблица установки в README подавала все строки одинаково.
    Для файла, который читает устанавливающий, это утверждение о чужой среде.
    Набор помечает непроверенное везде, кроме этого места.
    """
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    rows = [l for l in readme.splitlines()
            if l.startswith("|") and "skills/" in l]
    assert rows, "таблица ручной установки потерялась"
    for row in rows:
        assert "да" in row.lower() or "нет" in row.lower(), (
            "строка таблицы установки без пометки о проверке: %s" % row)
    for env in ("Cursor", "Copilot"):
        line = next((r for r in rows if env in r), None)
        assert line and "нет" in line.lower(), (
            "%s подан как проверенный, хотя прогона не было" % env)


def test_catalogue_budget_numbers_are_current():
    """Числа бюджета каталога в architecture.md обязаны совпадать с skills/.

    Правило 9 архитектуры объясняет, почему бюджет Codex тратится
    произведением «число навыков × длина описания», и иллюстрирует это
    измеренными числами. Иллюстрация устарела молча: текст называл ядро
    в 332 знака и `1c-build-and-db` в 228, когда на деле было 304 и 384 —
    описание `1c-build-and-db` расширили при починке дефекта, а этот абзац
    не тронули.

    Тот же класс, что и I-7 (`test_core_names_collected_skills_inline`):
    утверждение о содержимом набора, записанное прозой, живёт своей жизнью.
    Разница в том, что там устаревал состав, а здесь — замер, на который
    опирается правило.
    """
    arch = (ROOT / "skills" / "developing-1c-configurations"
            / "references" / "architecture.md").read_text(encoding="utf-8")

    заявлено = {}
    # Таблица лежит внутри нумерованного пункта и потому идёт с отступом —
    # шаблон, привязанный к самому началу строки, её не находил.
    for имя, знаков in re.findall(r"^\s*\|\s*`([a-z0-9-]+)`\s*\|\s*(\d+)\s*\|\s*$",
                                  arch, re.M):
        заявлено[имя] = int(знаков)
    assert заявлено, (
        "в architecture.md больше нет таблицы «Навык | Знаков в описании» — "
        "либо её убрали, либо сломали разметку; правило 9 без неё "
        "иллюстрируется ничем")

    фактически = {}
    for p in sorted((ROOT / "skills").glob("*/SKILL.md")):
        text = p.read_text(encoding="utf-8")
        fm = text.split("---", 2)[1]
        имя = re.search(r"^name:\s*(.+)$", fm, re.M).group(1).strip()
        описание = re.search(r"^description:\s*(.+)$", fm, re.M).group(1).strip()
        фактически[имя] = len(описание)

    assert заявлено == фактически, (
        "числа бюджета в architecture.md разошлись с skills/: заявлено %s, "
        "фактически %s" % (заявлено, фактически))


def test_section_skills_point_at_the_core():
    """Правило 12: навык раздела обязан указывать на ядро, и не одним именем.

    Правило 8 делает поднавык чисто реализационным — решения уровня плана
    живут в теле ядра. Исполнитель, открывший раздел с одной задачей и без
    контекста, обязан узнать оттуда, где лежит остальное.

    Бывший вопрос О-3 звучал как неразрешимый: Kilo ищет навык по точному
    имени без префикса, Claude Code под плагином — с префиксом, и одна
    строка не может быть верной в обеих средах. Ответ в том, что строк
    не одна — опознание идёт по первым словам описания ядра, одинаковым
    во всех средах, а имена даются оба.

    `1c-build-and-db` нёс этот блок с самого начала, `1c-queries` — нет,
    и пропажу не поймал ни один проверяльщик. Двенадцать оставшихся
    разделов пишутся по образцу; то, что держится вниманием автора,
    теряется на третьем.
    """
    core_dir = "developing-1c-configurations"
    core = (ROOT / "skills" / core_dir / "SKILL.md").read_text(encoding="utf-8")
    fm = core.split("---", 2)[1]
    описание = re.search(r"^description:\s*(.+)$", fm, re.M).group(1).strip()

    # Опознание идёт по НАЧАЛУ описания, но обрывать его поднавык вправе где
    # угодно — в тексте это «Разработка конфигураций 1С…» с многоточием.
    # Поэтому сторожится не фиксированное число слов (первая версия теста
    # требовала три и падала на живых файлах), а то, что процитировано
    # настоящее начало описания достаточной длины, чтобы опознать по нему.
    МИНИМУМ = 20

    def цитирует_начало(text):
        for n in range(len(описание), МИНИМУМ - 1, -1):
            if описание[:n] in text:
                return n
        return 0

    разделы = [p for p in sorted((ROOT / "skills").glob("*/SKILL.md"))
               if p.parent.name != core_dir]
    assert разделы, "в наборе не осталось навыков раздела — тест сторожит пустоту"

    беда = []
    for p in разделы:
        text = p.read_text(encoding="utf-8")
        if "REQUIRED BACKGROUND" not in text:
            беда.append("%s: нет блока REQUIRED BACKGROUND" % p.parent.name)
            continue
        сколько = цитирует_начало(text)
        if сколько < МИНИМУМ:
            беда.append("%s: не цитирует начало описания ядра (нужно не меньше "
                        "%d знаков подряд от %r)"
                        % (p.parent.name, МИНИМУМ, описание[:40]))
        if core_dir not in text:
            беда.append("%s: не названо голое имя ядра" % p.parent.name)
        if ("1c-agent-skills:" + core_dir) not in text:
            беда.append("%s: не названо имя ядра с префиксом плагина"
                        % p.parent.name)

    assert not беда, "правило 12 нарушено: " + "; ".join(беда)


# --- прибор не должен зависеть от переменной окружения ----------------------

def test_subprocess_calls_survive_ansi_output():
    """Набор был зелёным только потому, что PYTHONIOENCODING=utf-8 приходил
    из окружения.

    Дочерний Python кодирует stderr в ANSI-кодировке консоли. Родитель читает
    его как utf-8 и получает UnicodeDecodeError; subprocess отдаёт stdout/stderr
    как None, а следующая строка теста складывает None со строкой и падает
    с TypeError — вместо того, чтобы проверить то, что собиралась.

    Проверено 25.08.2026: `env -u PYTHONIOENCODING pytest` давал 10 падений
    в семи файлах, из которых пять мест уже чинили поштучно раньше. Поэтому
    правило, а не очередная точечная правка: любой захват текстового вывода
    подпроцесса обязан нести errors=, иначе декодирование может вернуть None.
    """
    import re as _re

    вызовы = []
    for p in sorted((ROOT / "tests").glob("*.py")):
        text = p.read_text(encoding="utf-8")
        for m in _re.finditer(r"subprocess\.(run|check_output|Popen)\s*\(", text):
            # тело вызова — до строки, где скобки сходятся
            i, глубина = m.end() - 1, 0
            while i < len(text):
                if text[i] == "(":
                    глубина += 1
                elif text[i] == ")":
                    глубина -= 1
                    if глубина == 0:
                        break
                i += 1
            тело = text[m.end():i]
            если_текст = "text=True" in тело or "universal_newlines=True" in тело
            if если_текст and "errors=" not in тело:
                строка = text[:m.start()].count("\n") + 1
                вызовы.append("%s:%d" % (p.name, строка))

    assert not вызовы, (
        "захват текстового вывода подпроцесса без errors= — при кириллице "
        "в выводе дочернего процесса декодирование вернёт None и тест упадёт "
        "с TypeError вместо своей проверки: " + ", ".join(вызовы))
