"""Проверка манифестов плагина: фронтматтер навыков и контракт Codex.

check-skills.py сверяется только с требованиями Anthropic к SKILL.md и о
плагинном манифесте Codex не знает ничего (см. находку Н-01 в
docs/reviews/2026-08-23-core-review.md). Этот проверяльщик закрывает ровно
тот пробел — второй чек, а не замена первого.

Источник контракта .codex-plugin/plugin.json — официальный валидатор Codex
из bundled-навыка plugin-creator (scripts/validate_plugin.py,
validate_manifest_shape): множество allowed_keys ниже списано с него дословно
22.08.2026 на codex.exe 0.147.0. Поле «hooks» в этот список НЕ входит и
валидатором отвергается, несмотря на то что references/plugin-json-spec.md
того же навыка документирует его как строковый путь («hooks (string): Hook
config path.») — сам справочник признаёт расхождение прямым текстом:
«Validation rejects unsupported manifest fields such as `hooks`».

Фронтматтер SKILL.md разбирается настоящим yaml.safe_load, а не регуляркой:
регулярка молча проходит мимо двоеточия с пробелом внутри description,
которое yaml.safe_load считает началом вложенного отображения (та же Н-01).

Возвращает ненулевой код при любом нарушении, поэтому годится для CI.

    python tools/check-manifests.py
"""
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

# Списано с validate_manifest_shape() в scripts/validate_plugin.py навыка
# plugin-creator (см. докстрока модуля). «hooks» сюда сознательно не входит.
CODEX_ALLOWED_KEYS = {
    "id", "name", "version", "description", "skills", "apps", "mcpServers",
    "interface", "author", "homepage", "repository", "license", "keywords",
}

# Та же строгая семверная регулярка, что в validate_plugin.py (SEMVER_RE).
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\."
    r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$")


def frontmatter_text(skill_md):
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return None
    return m.group(1)


def check_skill_frontmatter():
    """Возвращает список нарушений: фронтматтер обязан разбираться YAML."""
    bad = []
    for skill_md in sorted(SKILLS.rglob("SKILL.md")):
        fm_text = frontmatter_text(skill_md)
        if fm_text is None:
            bad.append("%s: нет фронтматтера" % skill_md.relative_to(ROOT))
            continue
        try:
            data = yaml.safe_load(fm_text)
        except yaml.YAMLError as exc:
            bad.append("%s: фронтматтер не разбирается YAML (%s)"
                        % (skill_md.relative_to(ROOT), str(exc).splitlines()[0]))
            continue
        if not isinstance(data, dict):
            bad.append("%s: фронтматтер не является отображением"
                        % skill_md.relative_to(ROOT))
            continue
        if "name" not in data or "description" not in data:
            bad.append("%s: нет обязательных полей name/description"
                        % skill_md.relative_to(ROOT))
    return bad


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_codex_manifest():
    """Возвращает список нарушений контракта .codex-plugin/plugin.json."""
    path = ROOT / ".codex-plugin" / "plugin.json"
    bad = []
    if not path.exists():
        return ["%s: файла нет" % path.relative_to(ROOT)]
    manifest = load_json(path)
    extra = set(manifest) - CODEX_ALLOWED_KEYS
    for key in sorted(extra):
        bad.append('.codex-plugin/plugin.json: поле "%s" отвергается '
                    "валидатором Codex" % key)
    return bad


def check_descriptions_agree():
    """Возвращает список нарушений: описания манифестов обязаны совпадать."""
    claude_path = ROOT / ".claude-plugin" / "plugin.json"
    codex_path = ROOT / ".codex-plugin" / "plugin.json"
    if not claude_path.exists() or not codex_path.exists():
        return []
    a = load_json(claude_path).get("description", "")
    b = load_json(codex_path).get("description", "")
    if a != b:
        return ["описание .claude-plugin/plugin.json и .codex-plugin/plugin.json разошлось"]
    return []


def check_version():
    """Версия объявлена ровно один раз и соответствует semver."""
    bad = []
    claude_path = ROOT / ".claude-plugin" / "plugin.json"
    market_path = ROOT / ".claude-plugin" / "marketplace.json"
    codex_path = ROOT / ".codex-plugin" / "plugin.json"

    versions = {}
    if claude_path.exists():
        versions[".claude-plugin/plugin.json"] = load_json(claude_path).get("version")
    if codex_path.exists():
        versions[".codex-plugin/plugin.json"] = load_json(codex_path).get("version")

    for src, v in versions.items():
        if not v:
            bad.append("%s: нет поля version" % src)
        elif not SEMVER.fullmatch(v):
            bad.append('%s: версия "%s" не соответствует semver' % (src, v))

    if market_path.exists():
        market = load_json(market_path)
        for entry in market.get("plugins", []):
            if "version" in entry:
                bad.append(
                    ".claude-plugin/marketplace.json: версия продублирована в записи "
                    'маркета "%s"; при расхождении молча побеждает plugin.json'
                    % entry.get("name", "?"))
    return bad


def main():
    checks = [
        check_skill_frontmatter(),
        check_codex_manifest(),
        check_descriptions_agree(),
        check_version(),
    ]
    total = 0
    for bad in checks:
        for b in bad:
            print("[!] %s" % b)
        total += len(bad)

    print()
    print("манифесты проверены, нарушений: %d" % total)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
