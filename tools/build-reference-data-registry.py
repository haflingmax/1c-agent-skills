"""Механический слой описи данных референсных наборов (этап РАЗБОР-1б).

Навыки описаны отдельно, `build-reference-registry.py`. Здесь — всё остальное
содержимое обоих наборов, разложенное на шесть классов:

  docs                 спецификации и руководства в корне набора
  rules                правила разработки (только у claude-code-skills-1c)
  справочники навыков  .md рядом с SKILL.md
  обвязка              commands/, tools/, hooks/, scripts/ в корне
  скрипты навыков      .py и .ps1 внутри каталогов навыков
  тесты                наборы случаев — только структура семейств

Извлекается то, что не требует суждения: заголовок, первый абзац, число
разделов, шапка скрипта, его ключи, зовёт ли он платформу. Пересказ содержания
и отнесение к нашим 16 разделам — работа читающего слоя.

Решение 16 общего плана: чужой материал не переносится. Поэтому по скриптам
и тестам берётся только назначение — знать надо, какая возможность там есть,
а не как она написана.

Запуск: PYTHONIOENCODING=utf-8 python tools/build-reference-data-registry.py
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SETS = [
    {"ключ": "cc", "репозиторий": "cc-1c-skills", "каталог_навыков": ".claude/skills"},
    {"ключ": "ccs", "репозиторий": "claude-code-skills-1c", "каталог_навыков": "skills"},
]

HARNESS_DIRS = ["commands", "tools", "hooks", "scripts"]
SCRIPT_SUFFIXES = {".py", ".ps1", ".psm1", ".sh", ".cmd", ".bat", ".os"}
PLATFORM = re.compile(r"\b(1cv8|ibcmd|rac\.exe|ras\.exe)\b", re.IGNORECASE)


def fail(message, code=2):
    sys.stdout.write(message + "\n")
    raise SystemExit(code)


def strip_frontmatter(text):
    """Тело без YAML-шапки. У файлов rules/ шапка несёт маски путей."""
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    return text[end + 4:] if end != -1 else text


def md_title(text):
    """Заголовок первого уровня. Его может не быть — это факт, а не сбой."""
    for line in strip_frontmatter(text).splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def md_lead(text):
    """Первый содержательный абзац после заголовка.

    Больше механический слой брать не вправе: пересказ — уже суждение.
    """
    body = strip_frontmatter(text)
    lines, out, started = body.splitlines(), [], False
    for line in lines:
        s = line.strip()
        if not started:
            if s.startswith("# "):
                started = True
            continue
        if not s or set(s) <= set("-=*_"):
            if out:
                break
            continue
        if s.startswith("#"):
            break
        out.append(s)
    return " ".join(out).strip()


def md_headings(text):
    """Число разделов ниже заголовка — грубая мера подробности."""
    return sum(1 for line in strip_frontmatter(text).splitlines()
               if re.match(r"^#{2,6}\s", line))


def script_header(text):
    """Шапка скрипта: комментарии сверху, без shebang.

    Авторы обоих наборов пишут в шапке назначение и версию, так что это
    и есть готовое «что делает», взятое из файла, а не придуманное.
    """
    lines = text.splitlines()
    if lines and lines[0].startswith("#!"):
        lines = lines[1:]
    out = []
    if lines and lines[0].strip().startswith("<#"):
        for line in lines[1:]:
            if line.strip().startswith("#>"):
                break
            out.append(line.strip())
        return " ".join(out).strip()
    if lines and lines[0].strip().startswith(('"""', "'''")):
        q = lines[0].strip()[:3]
        first = lines[0].strip()[3:]
        if first.endswith(q):
            return first[:-3].strip()
        out.append(first)
        for line in lines[1:]:
            if q in line:
                out.append(line.split(q)[0].strip())
                break
            out.append(line.strip())
        return " ".join(x for x in out if x).strip()
    for line in lines:
        s = line.strip()
        if s.startswith("#"):
            out.append(s.lstrip("#").strip())
        elif out or s:
            break
    return " ".join(x for x in out if x).strip()


def calls_platform(text):
    """Зовёт ли объект платформу 1С. Факт, а не суждение."""
    return bool(PLATFORM.search(text))


def cli_flags(text):
    """Ключи командной строки: argparse у Python, param() у PowerShell."""
    flags = re.findall(r"add_argument\(\s*['\"](--[\w-]+)['\"]", text)
    if flags:
        return sorted(set(flags))
    block = re.search(r"param\s*\((.*?)\n\s*\)", text, re.S | re.IGNORECASE)
    if block:
        return sorted({"-" + n for n in re.findall(r"\$(\w+)", block.group(1))})
    return []


def owning_skill(path, skills_root):
    """Навык, которому принадлежит файл. Берётся из пути, а не из содержимого.

    Справочник и скрипт живут внутри каталога навыка, и это готовая привязка:
    разбирать их в отрыве от навыка бессмысленно — они его части.
    """
    try:
        rel = path.relative_to(skills_root)
    except ValueError:
        return ""
    return rel.parts[0] if len(rel.parts) > 1 else ""


def pair_key(class_name, filename):
    """Ключ спаривания одноимённых файлов: docs/ форкнут так же, как навыки."""
    return "%s/%s" % (class_name, filename)


def read_md(path, ref_root, meta, class_name, skill=""):
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "набор": meta["ключ"],
        "класс": class_name,
        "имя": path.name,
        "путь": path.relative_to(ref_root).as_posix(),
        "заголовок": md_title(text),
        "первый_абзац": md_lead(text)[:400],
        "навык": skill,
        "разделов": md_headings(text),
        "знаков": len(text),
        "пара": None,
    }


def read_script(path, ref_root, meta, class_name, skill=""):
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "набор": meta["ключ"],
        "класс": class_name,
        "имя": path.name,
        "путь": path.relative_to(ref_root).as_posix(),
        "шапка": script_header(text)[:300],
        "ключи": cli_flags(text)[:12],
        "навык": skill,
        "зовёт_платформу": calls_platform(text),
        "знаков": len(text),
        "пара": None,
    }


def collect(ref_root):
    объекты, семейства = [], []
    for meta in SETS:
        repo = ref_root / meta["репозиторий"]
        if not repo.is_dir():
            fail("[ошибка] нет %s — набор не выкачан." % repo)
        skills_root = repo / meta["каталог_навыков"]

        for p in sorted((repo / "docs").rglob("*.md")) if (repo / "docs").is_dir() else []:
            объекты.append(read_md(p, ref_root, meta, "docs"))
        for p in sorted((repo / "rules").rglob("*")) if (repo / "rules").is_dir() else []:
            if p.is_file():
                объекты.append(read_md(p, ref_root, meta, "rules"))

        if skills_root.is_dir():
            for p in sorted(skills_root.rglob("*.md")):
                if p.name != "SKILL.md":
                    объекты.append(read_md(p, ref_root, meta, "справочники навыков",
                                           owning_skill(p, skills_root)))
            for p in sorted(skills_root.rglob("*")):
                if p.is_file() and p.suffix.lower() in SCRIPT_SUFFIXES:
                    объекты.append(read_script(p, ref_root, meta, "скрипты навыков",
                                               owning_skill(p, skills_root)))

        for sub in HARNESS_DIRS:
            d = repo / sub
            if not d.is_dir():
                continue
            for p in sorted(d.rglob("*")):
                if not p.is_file():
                    continue
                if p.suffix.lower() in SCRIPT_SUFFIXES:
                    объекты.append(read_script(p, ref_root, meta, "обвязка"))
                elif p.suffix.lower() == ".md":
                    объекты.append(read_md(p, ref_root, meta, "обвязка"))

        cases = repo / "tests" / "skills" / "cases"
        if cases.is_dir():
            for d in sorted(cases.iterdir()):
                if not d.is_dir():
                    continue
                files = [f for f in d.rglob("*") if f.is_file()]
                суффиксы = sorted({f.suffix.lower() for f in files if f.suffix})
                семейства.append({
                    "набор": meta["ключ"],
                    "семейство": d.name,
                    "файлов": len(files),
                    "форматы": суффиксы[:8],
                    "путь": d.relative_to(ref_root).as_posix(),
                })
    return объекты, семейства


def link_docs_pairs(объекты):
    """Одноимённые файлы docs/ и rules/ — две версии одного, как у навыков."""
    index = {}
    for o in объекты:
        if o["класс"] not in ("docs", "rules"):
            continue
        index.setdefault(pair_key(o["класс"], o["имя"]), []).append(o)
    for group in index.values():
        if len(group) != 2:
            continue
        a, b = group
        a["пара"] = {"набор": b["набор"], "путь": b["путь"]}
        b["пара"] = {"набор": a["набор"], "путь": a["путь"]}


def build(ref_root):
    ref_root = Path(ref_root)
    if not ref_root.is_dir():
        fail("[ошибка] нет каталога %s.\n"
             "Референсные наборы лежат под gitignore и есть не на каждой машине.\n"
             "Выкачать:\n"
             "  git clone --depth 1 https://github.com/Nikolay-Shirokov/cc-1c-skills.git _ref/cc-1c-skills\n"
             "  git clone --depth 1 https://github.com/Desko77/claude-code-skills-1c.git _ref/claude-code-skills-1c\n"
             "Опись не собрана. Пустой реестр не записан намеренно." % ref_root)

    объекты, семейства = collect(ref_root)
    link_docs_pairs(объекты)
    объекты.sort(key=lambda o: (o["класс"], o["набор"], o["путь"]))
    семейства.sort(key=lambda f: (f["набор"], f["семейство"]))

    классы = []
    for name in ["docs", "rules", "справочники навыков", "обвязка",
                 "скрипты навыков", "тесты"]:
        if name == "тесты":
            классы.append({"класс": name,
                           "файлов": sum(f["файлов"] for f in семейства),
                           "знаков": 0,
                           "семейств": len(семейства)})
            continue
        rows = [o for o in объекты if o["класс"] == name]
        классы.append({"класс": name, "файлов": len(rows),
                       "знаков": sum(o["знаков"] for o in rows)})

    return {
        "что_это": "Механическая опись данных референсных наборов, этап РАЗБОР-1б. "
                   "Ни выжимки, ни отнесения к разделу, ни решения о судьбе объекта.",
        "классы": классы,
        "объекты": объекты,
        "семейства_тестов": семейства,
    }


def as_markdown(reg):
    L = []
    a = L.append
    a("# Опись данных референсных наборов (РАЗБОР-1б)")
    a("")
    a("Порождается `tools/build-reference-data-registry.py` из `_ref/` под gitignore.")
    a("Навыки описаны отдельно — `docs/reference-registry.md`.")
    a("")
    a("**Решения о судьбе объекта здесь нет и не будет.** Опись отвечает на вопрос")
    a("«что есть»; чужой материал не переносится вовсе (решение 16 общего плана).")
    a("")
    a("| Класс | Файлов | Знаков |")
    a("|---|---|---|")
    for c in reg["классы"]:
        a("| %s | %d | %s |" % (c["класс"], c["файлов"],
                                "%d" % c["знаков"] if c["знаков"] else "—"))
    a("")

    for name in ["docs", "rules"]:
        rows = [o for o in reg["объекты"] if o["класс"] == name]
        if not rows:
            continue
        a("## %s — %d" % (name, len(rows)))
        a("")
        a("| Файл | Набор | Заголовок | Разделов | Знаков | Пара |")
        a("|---|---|---|---|---|---|")
        for o in rows:
            a("| `%s` | %s | %s | %d | %d | %s |"
              % (o["имя"], o["набор"], o["заголовок"].replace("|", "\\|") or "—",
                 o["разделов"], o["знаков"], "да" if o["пара"] else "—"))
        a("")

    a("## Семейства тестовых случаев — %d" % len(reg["семейства_тестов"]))
    a("")
    a("По решению 16 берётся только структура: чужой код не переносится, а знать")
    a("надо, какая возможность проверяется, а не как написан случай.")
    a("")
    a("| Семейство | Набор | Файлов | Форматы |")
    a("|---|---|---|---|")
    for f in reg["семейства_тестов"]:
        a("| `%s` | %s | %d | %s |"
          % (f["семейство"], f["набор"], f["файлов"], ", ".join(f["форматы"]) or "—"))
    a("")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ref", default=str(ROOT / "_ref"))
    ap.add_argument("--out-json", default=str(ROOT / "docs" / "reference-data-registry.json"))
    ap.add_argument("--out-md", default=str(ROOT / "docs" / "reference-data-registry.md"))
    args = ap.parse_args()

    reg = build(args.ref)
    Path(args.out_json).write_text(
        json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    Path(args.out_md).write_text(as_markdown(reg), encoding="utf-8", newline="\n")

    for c in reg["классы"]:
        print("  %-22s %5d файлов %10s знаков"
              % (c["класс"], c["файлов"], c["знаков"] or "—"))
    print("семейств тестов: %d" % len(reg["семейства_тестов"]))
    print("записано: %s, %s" % (args.out_json, args.out_md))


if __name__ == "__main__":
    main()
