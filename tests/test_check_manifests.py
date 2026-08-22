"""Проверка манифестов плагина и разбора фронтматтера настоящим YAML.

Соответствует находкам Н-04 и Н-01 из docs/reviews/2026-08-23-core-review.md.
Запуск: python -m pytest tests/test_check_manifests.py -v
"""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    assert m, "нет фронтматтера в %s" % path
    return m.group(1)


def test_frontmatter_is_valid_yaml():
    """Н-04: фронтматтер обязан разбираться настоящим YAML, не регуляркой."""
    for skill_md in sorted((ROOT / "skills").rglob("SKILL.md")):
        data = yaml.safe_load(frontmatter(skill_md))
        assert isinstance(data, dict), skill_md
        assert "name" in data and "description" in data, skill_md


def test_codex_manifest_has_no_rejected_fields():
    """Н-04: поле hooks официальный валидатор Codex отвергает."""
    m = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert "hooks" not in m, "поле hooks отвергается валидатором Codex"


def test_plugin_descriptions_agree():
    """М-09: два манифеста не должны расходиться в описании."""
    a = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    b = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert a["description"] == b["description"], "описания манифестов разошлись"


def test_version_declared_once():
    """М-05: версия не должна дублироваться в манифесте и в записи маркета."""
    mk = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    entry = mk["plugins"][0]
    assert "version" not in entry, (
        "версия объявлена и в plugin.json, и в записи маркета; "
        "при расхождении молча побеждает plugin.json")
