"""Проверка манифестов плагина и разбора фронтматтера настоящим YAML.

Соответствует находке Н-01 и мелким М-05, М-09 из
docs/reviews/2026-08-23-core-review.md.
Запуск: python -m pytest tests/test_check_manifests.py -v

I-4 финального ревью: этот файл дублировал утверждения `tools/check-manifests.py`
вручную и про сам инструмент не знал. Логика `CODEX_ALLOWED_KEYS`, `SEMVER`,
`check_version`, `check_descriptions_agree` не была покрыта ни одним прогоном —
инструмент был написан, но в контур не встал. Ниже два слоя:

1. проверки живого дерева (были и раньше) — набор в репозитории исправен;
2. проверки самого инструмента: он импортируется, ему подсовываются заведомо
   негодные манифесты во временном каталоге, и проверяется, что он их ловит.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "check-manifests.py"

_spec = importlib.util.spec_from_file_location("check_manifests", TOOL)
mod = importlib.util.module_from_spec(_spec)
sys.modules["check_manifests"] = mod
_spec.loader.exec_module(mod)


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    assert m, "нет фронтматтера в %s" % path
    return m.group(1)


def test_frontmatter_is_valid_yaml():
    """Н-01: фронтматтер обязан разбираться настоящим YAML, не регуляркой."""
    for skill_md in sorted((ROOT / "skills").rglob("SKILL.md")):
        data = yaml.safe_load(frontmatter(skill_md))
        assert isinstance(data, dict), skill_md
        assert "name" in data and "description" in data, skill_md


def test_codex_manifest_has_no_rejected_fields():
    """Н-01: поле hooks официальный валидатор Codex отвергает."""
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


# --- Слой 2: под собственный тест ставится сам инструмент (I-4) ---

def fake_tree(tmp_path, monkeypatch, claude=None, codex=None, market=None,
              frontmatter=None):
    """Собирает временное дерево манифестов и переключает инструмент на него."""
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".codex-plugin").mkdir()
    skill_dir = tmp_path / "skills" / "demo"
    skill_dir.mkdir(parents=True)

    if claude is not None:
        (tmp_path / ".claude-plugin" / "plugin.json").write_text(
            json.dumps(claude, ensure_ascii=False), encoding="utf-8")
    if codex is not None:
        (tmp_path / ".codex-plugin" / "plugin.json").write_text(
            json.dumps(codex, ensure_ascii=False), encoding="utf-8")
    if market is not None:
        (tmp_path / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps(market, ensure_ascii=False), encoding="utf-8")
    if frontmatter is None:
        frontmatter = "name: demo\ndescription: Демо."
    (skill_dir / "SKILL.md").write_text(
        "---\n%s\n---\n\nтело\n" % frontmatter, encoding="utf-8")

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "SKILLS", tmp_path / "skills")


OK_MANIFEST = {"name": "demo", "description": "Демо.", "version": "0.2.0"}


def test_tool_catches_colon_in_description(tmp_path, monkeypatch):
    """Н-01 глазами инструмента: двоеточие в описании ломает YAML."""
    fake_tree(tmp_path, monkeypatch,
              frontmatter="name: demo\ndescription: Демо: и ещё раз демо.")
    bad = mod.check_skill_frontmatter()
    assert bad and "не разбирается YAML" in bad[0], bad


def test_tool_accepts_valid_frontmatter(tmp_path, monkeypatch):
    fake_tree(tmp_path, monkeypatch)
    assert mod.check_skill_frontmatter() == []


def test_tool_catches_field_rejected_by_codex(tmp_path, monkeypatch):
    """CODEX_ALLOWED_KEYS: hooks официальный валидатор Codex отвергает."""
    codex = dict(OK_MANIFEST, hooks={})
    fake_tree(tmp_path, monkeypatch, claude=OK_MANIFEST, codex=codex)
    bad = mod.check_codex_manifest()
    assert bad and "hooks" in bad[0], bad
    assert "hooks" not in mod.CODEX_ALLOWED_KEYS


def test_tool_catches_diverged_descriptions(tmp_path, monkeypatch):
    """М-09: описания двух манифестов не должны расходиться."""
    fake_tree(tmp_path, monkeypatch,
              claude=OK_MANIFEST, codex=dict(OK_MANIFEST, description="Другое."))
    assert mod.check_descriptions_agree(), "расхождение описаний не поймано"


def test_tool_catches_diverged_versions(tmp_path, monkeypatch):
    """I-4: равенство версий было объявлено в docs/releasing.md, но не проверялось.

    Воспроизведено на живом дереве до правки: 0.2.0 против 0.3.0 давало
    «манифесты проверены, нарушений: 0», код 0.
    """
    fake_tree(tmp_path, monkeypatch,
              claude=OK_MANIFEST, codex=dict(OK_MANIFEST, version="0.3.0"))
    bad = mod.check_version()
    assert any("версии манифестов разошлись" in b for b in bad), bad


def test_tool_accepts_equal_versions(tmp_path, monkeypatch):
    fake_tree(tmp_path, monkeypatch, claude=OK_MANIFEST, codex=OK_MANIFEST)
    assert mod.check_version() == []


@pytest.mark.parametrize("version", ["0.2", "1.0.0.0", "v1.0.0", "01.2.3", ""])
def test_tool_rejects_non_semver(tmp_path, monkeypatch, version):
    """SEMVER — та же строгая регулярка, что у валидатора Codex."""
    fake_tree(tmp_path, monkeypatch,
              claude=dict(OK_MANIFEST, version=version),
              codex=dict(OK_MANIFEST, version=version))
    bad = mod.check_version()
    assert bad, "версия %r принята" % version


def test_tool_catches_version_duplicated_in_marketplace(tmp_path, monkeypatch):
    """М-05: версия в записи маркета молча проигрывает plugin.json."""
    fake_tree(tmp_path, monkeypatch, claude=OK_MANIFEST, codex=OK_MANIFEST,
              market={"plugins": [{"name": "demo", "version": "0.9.0"}]})
    bad = mod.check_version()
    assert any("marketplace.json" in b for b in bad), bad


def test_tool_returns_nonzero_on_violation(tmp_path, monkeypatch, capsys):
    """Ненулевой код — то, ради чего инструмент годится для CI."""
    fake_tree(tmp_path, monkeypatch,
              claude=OK_MANIFEST, codex=dict(OK_MANIFEST, hooks={}))
    assert mod.main() == 1
    assert "hooks" in capsys.readouterr().out


def test_tool_returns_zero_on_clean_tree(tmp_path, monkeypatch, capsys):
    fake_tree(tmp_path, monkeypatch, claude=OK_MANIFEST, codex=OK_MANIFEST)
    assert mod.main() == 0
    assert "нарушений: 0" in capsys.readouterr().out


def test_tool_is_wired_into_acceptance_and_readme():
    """I-4: проверка написана — теперь она ещё и вызывается."""
    acceptance = (ROOT / "tools" / "run-acceptance.ps1").read_text(encoding="utf-8-sig")
    assert "check-manifests.py" in acceptance, (
        "tools/run-acceptance.ps1 не зовёт tools/check-manifests.py")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "check-manifests.py" in readme, (
        "README не называет tools/check-manifests.py в разделе проверок")
