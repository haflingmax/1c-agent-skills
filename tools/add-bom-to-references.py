"""Ставит метку порядка байтов UTF-8 в начало каждого справочника навыка.

Зачем — см. tests/test_references_have_bom.py. SKILL.md не трогается:
перед его YAML-шапкой BOM может помешать загрузчику навыков.

Запуск: python tools/add-bom-to-references.py
Повторный запуск безвреден: файл, уже начинающийся с BOM, не меняется.
Код возврата: 0 — готово; 3 — записанное отвергнуто tools/check-manifests.py.

Скрипт пишет в skills/ и потому подчиняется правилу C-1
(tests/test_tools_write_guard.py): заканчивается прогоном
tools/check-manifests.py и падает при его ненулевом коде.
"""
import subprocess
import sys
from pathlib import Path

BOM = b"\xef\xbb\xbf"
ROOT = Path(__file__).resolve().parent.parent
CHECK_MANIFESTS = ROOT / "tools" / "check-manifests.py"


def verify_manifests():
    """Прогоняет tools/check-manifests.py отдельным процессом; ненулевой код — падаем."""
    proc = subprocess.run(
        [sys.executable, str(CHECK_MANIFESTS)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(((proc.stdout or "") + (proc.stderr or "")).strip())
    if proc.returncode != 0:
        print("[ошибка] записанное отвергнуто tools/check-manifests.py (код %d)"
              % proc.returncode)
        raise SystemExit(3)


def main():
    поставлено = 0
    всего = 0
    for путь in sorted(ROOT.glob("skills/*/references/*.md")):
        всего += 1
        байты = путь.read_bytes()
        if байты.startswith(BOM):
            continue
        байты.decode("utf-8")  # не UTF-8 — пусть упадёт здесь, а не испортит файл
        путь.write_bytes(BOM + байты)
        поставлено += 1
    print("справочников: %d, BOM поставлен в %d" % (всего, поставлено))
    verify_manifests()


if __name__ == "__main__":
    main()
