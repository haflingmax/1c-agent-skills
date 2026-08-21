"""Проставляет в cli-keys.json признак слитного значения.

Слитный ключ записан в документации как /Имя<значение> — без пробела.
Таких 12; у остальных значение отделяется пробелом либо его нет вовсе.
Источник: _its/cmdline/its-pril7-full.json, приложение 7 руководства администратора.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_its" / "cmdline" / "its-pril7-full.json"
DST = ROOT / "skills" / "1c-build-and-db" / "scripts" / "cli-keys.json"


def glued_keys(text):
    text = text.replace("‑", "-").replace(" ", " ")
    blocks, cur = [], []
    for line in text.split("\n"):
        if line.strip():
            cur.append(line.strip())
        elif cur:
            blocks.append(" ".join(cur))
            cur = []
    if cur:
        blocks.append(" ".join(cur))
    found = set()
    for b in blocks:
        m = re.match(r"^(/[A-Za-z][A-Za-z0-9_]*)(.?)", b)
        if m and m.group(2) == "<":
            found.add(m.group(1))
    return found


def main():
    glued = glued_keys(json.loads(SRC.read_text(encoding="utf-8"))["text"])
    doc = json.loads(DST.read_text(encoding="utf-8"))
    for k, v in doc["ключи"].items():
        v["glued"] = k in glued
    DST.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("слитных ключей:", sum(1 for v in doc["ключи"].values() if v["glued"]))


if __name__ == "__main__":
    main()
