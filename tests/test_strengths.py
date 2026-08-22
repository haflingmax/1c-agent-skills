"""Регресс сильных сторон набора.

Каждый тест соответствует свойству, отмеченному ревью как ценное. Смысл —
не дать доработке сломать то, что уже сделано верно. Источник формулировок:
docs/reviews/2026-08-23-core-review.md, раздел «Сильные стороны» (43 пункта).

Сюда попали только машинно проверяемые пункты — те, где сама формулировка
описывает факт о файлах репозитория, а не историческое действие или вывод
живого прогона. Остальные 21 из 43 сведены для человека в
docs/reviews/2026-08-23-strengths-manual.md — там же объяснено, почему
каждый из них не выражается тестом.
"""
import json
import re
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
    """Признак предпосылки вместо закрытого списка вопросов — пара
    «Развилка?» / «Своя починка?» в ядре, открытая с обоих концов."""
    text = (ROOT / "skills" / "developing-1c-configurations" / "SKILL.md").read_text(encoding="utf-8")
    assert "Развилка?" in text, "вопрос «Развилка?» потерялся"
    assert "Своя починка?" in text, "вопрос «Своя починка?» потерялся"
