"""Механический слой описи референсных наборов (этап РАЗБОР-1а).

Собирает реестр навыков двух референсных наборов под MIT. Извлекается только
то, что не требует суждения: путь, имя и описание из фронтматтера, объём,
состав каталога навыка, связь с одноимённым навыком другого набора.

Чего здесь НЕТ и быть не должно: выжимки содержания, отнесения к одному из
16 наших разделов, и тем более вердикта о судьбе объекта. Это работа
читающего слоя и следующего этапа. Механический слой ценен ровно тем, что
его нельзя выдумать: каждое поле перепроверяется открытием файла по пути.

Источник — _ref/ под gitignore. Наборы:
  cc-1c-skills          Николай Широков, MIT, https://github.com/Nikolay-Shirokov/cc-1c-skills
  claude-code-skills-1c Desko77, MIT, https://github.com/Desko77/claude-code-skills-1c

Второй набор — производный от первого: его CHANGELOG прямо ссылается на
cc-1c-skills и на va-ai того же автора. Поэтому имена спариваются: навык
«cf-edit» первого набора и «1c-cf-edit» второго — две версии одного, а не
два независимых источника.

Запуск: PYTHONIOENCODING=utf-8 python tools/build-reference-registry.py
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SETS = [
    {
        "ключ": "cc",
        "репозиторий": "cc-1c-skills",
        "каталог_навыков": ".claude/skills",
        "автор": "Николай Широков",
        "ссылка": "https://github.com/Nikolay-Shirokov/cc-1c-skills",
        "лицензия": "MIT",
    },
    {
        "ключ": "ccs",
        "репозиторий": "claude-code-skills-1c",
        "каталог_навыков": "skills",
        "автор": "Desko77",
        "ссылка": "https://github.com/Desko77/claude-code-skills-1c",
        "лицензия": "MIT",
    },
]

PREFIX = "1c-"


def fail(message, code=2):
    sys.stdout.write(message + "\n")
    raise SystemExit(code)


def parse_frontmatter(text):
    """Пары ключ-значение из YAML-фронтматтера, без внешних зависимостей.

    Разбор идёт по первому двоеточию КЛЮЧА, а не строки: двоеточие внутри
    значения к значению и относится. Вложенные списки (allowed-tools)
    пропускаются — механическому слою они не нужны.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out = {}
    for line in text[3:end].splitlines():
        if not line.strip() or line.startswith((" ", "\t", "-", "#")):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        out[key.strip()] = value.strip()
    return out


def body_lines(text):
    """Число строк тела — после фронтматтера, чтобы сравнивать сравнимое."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    return len([l for l in text.splitlines() if l.strip()])


def paired_name(name):
    """Имя того же навыка в производном наборе: «cf-edit» -> «1c-cf-edit»."""
    return name if name.startswith(PREFIX) else PREFIX + name


def head_commit(repo_dir):
    """Ревизия клона: без неё опись нельзя привязать ко времени."""
    try:
        r = subprocess.run(
            ["git", "-c", "safe.directory=*", "-C", str(repo_dir),
             "log", "-1", "--format=%h|%ad", "--date=short"],
            capture_output=True, text=True, encoding="utf-8", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return {"коммит": None, "дата": None}
    if r.returncode != 0:
        return {"коммит": None, "дата": None}
    sha, _, date = r.stdout.strip().partition("|")
    return {"коммит": sha or None, "дата": date or None}


def count_files(path):
    return len([p for p in path.rglob("*") if p.is_file()]) if path.is_dir() else 0


def read_skill(skill_dir, meta, ref_root):
    """Одна запись реестра. Каждое поле — из файла, ни одного из головы."""
    skill_md = skill_dir / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)
    reference = skill_dir / "reference.md"
    return {
        "набор": meta["ключ"],
        "каталог": skill_dir.name,
        "имя": fm.get("name") or skill_dir.name,
        "имя_из_фронтматтера": bool(fm.get("name")),
        "описание": fm.get("description", ""),
        "подсказка_аргументов": fm.get("argument-hint", ""),
        "путь": skill_md.relative_to(ref_root).as_posix(),
        "знаков_skill": len(text),
        "строк_тела": body_lines(text),
        "справочник": reference.is_file(),
        "знаков_справочника": len(reference.read_text(encoding="utf-8", errors="replace"))
                              if reference.is_file() else 0,
        "скриптов": count_files(skill_dir / "scripts"),
        "проверок": count_files(skill_dir / "evals"),
        "пара": None,
    }


def link_pairs(skills):
    """Связывает две версии одного навыка. Ссылка двусторонняя.

    Односторонняя связь врала бы при обходе реестра с любой стороны, кроме
    одной, а обходить его будут с обеих: разбор пойдёт по разделам, а не
    по наборам.
    """
    by_key = {(s["набор"], s["имя"]): s for s in skills}
    for s in skills:
        if s["набор"] != "cc":
            continue
        other = by_key.get(("ccs", paired_name(s["имя"])))
        if not other:
            continue
        s["пара"] = {"набор": other["набор"], "имя": other["имя"], "путь": other["путь"]}
        other["пара"] = {"набор": s["набор"], "имя": s["имя"], "путь": s["путь"]}


def build(ref_root):
    ref_root = Path(ref_root)
    if not ref_root.is_dir():
        fail("[ошибка] нет каталога %s.\n"
             "Референсные наборы лежат под gitignore и есть не на каждой машине.\n"
             "Выкачать:\n"
             "  git clone --depth 1 https://github.com/Nikolay-Shirokov/cc-1c-skills.git _ref/cc-1c-skills\n"
             "  git clone --depth 1 https://github.com/Desko77/claude-code-skills-1c.git _ref/claude-code-skills-1c\n"
             "Опись не собрана. Пустой реестр не записан намеренно: молчаливая\n"
             "пустота хуже понятного отказа." % ref_root)

    наборы, навыки = [], []
    for meta in SETS:
        repo_dir = ref_root / meta["репозиторий"]
        skills_dir = repo_dir / meta["каталог_навыков"]
        if not skills_dir.is_dir():
            fail("[ошибка] в %s нет каталога навыков %s — набор выкачан не полностью "
                 "или сменил раскладку." % (repo_dir, meta["каталог_навыков"]))
        found = sorted(p.parent for p in skills_dir.glob("*/SKILL.md"))
        навыки.extend(read_skill(d, meta, ref_root) for d in found)
        наборы.append(dict(meta, навыков=len(found), **head_commit(repo_dir)))

    link_pairs(навыки)
    навыки.sort(key=lambda s: (s["набор"], s["имя"]))
    парных = sum(1 for s in навыки if s["пара"])

    return {
        "что_это": "Механическая опись референсных наборов, этап РАЗБОР-1а. "
                   "Ни выжимки, ни отнесения к разделу, ни вердикта здесь нет.",
        "наборы": наборы,
        "всего_навыков": len(навыки),
        "навыков_в_паре": парных,
        "различных_навыков": len(навыки) - парных // 2,
        "навыки": навыки,
    }


def read_reading_layer(path):
    """Читающий слой, если он уже сведён. Его отсутствие — не ошибка."""
    path = Path(path)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {r["единица"]: r for r in data.get("записи", [])}


def as_markdown(reg, reading=None):
    reading = reading or {}
    L = []
    a = L.append
    a("# Опись референсных наборов (РАЗБОР-1а)")
    a("")
    a("Порождается `tools/build-reference-registry.py` из `_ref/` под gitignore.")
    a("Правится не руками, а пересборкой.")
    a("")
    if reading:
        a("Два слоя. **Механический** — из файлов, воспроизводится побайтно.")
        a("**Читающий** — суждение агентов-читателей, лежит в")
        a("`docs/reference-reading.json` и проверяется на входе:")
        a("каждая запись опирается на цитату с путём и строкой.")
    else:
        a("**Только механический слой.** Читающий ещё не сведён.")
    a("")
    a("**Решения о судьбе объекта здесь нет и не будет.** Опись отвечает")
    a("на вопрос «что есть», решает этап РАЗБОР-2, попунктно.")
    a("")
    a("## Источники")
    a("")
    a("| Набор | Автор | Лицензия | Навыков | Ревизия | Дата |")
    a("|---|---|---|---|---|---|")
    for s in reg["наборы"]:
        a("| [%s](%s) | %s | %s | %d | `%s` | %s |"
          % (s["репозиторий"], s["ссылка"], s["автор"], s["лицензия"],
             s["навыков"], s["коммит"] or "—", s["дата"] or "—"))
    a("")
    a("## Счёт")
    a("")
    a("Навыков всего: **%d**. Из них состоят в паре: **%d** (%d пар)."
      % (reg["всего_навыков"], reg["навыков_в_паре"], reg["навыков_в_паре"] // 2))
    a("Различных навыков — **%d**." % reg["различных_навыков"])
    a("")
    a("Пара — это две версии одного навыка. `claude-code-skills-1c` производен")
    a("от `cc-1c-skills`: его `CHANGELOG.md` ссылается на первый набор и на")
    a("`va-ai` того же автора. Имена спариваются по правилу «`X` ↔ `1c-X`».")
    a("Разбирать пару надо вместе, сравнивая версии, а не дважды по отдельности.")
    a("")
    if reading:
        a(_by_section(reg, reading))

    for meta in SETS:
        rows = [s for s in reg["навыки"] if s["набор"] == meta["ключ"]]
        a("## %s (%d)" % (meta["репозиторий"], len(rows)))
        a("")
        a("| Навык | Знаков | Строк тела | Справочник | Скриптов | Проверок | Пара |")
        a("|---|---|---|---|---|---|---|")
        for s in rows:
            a("| `%s` | %d | %d | %s | %d | %d | %s |"
              % (s["имя"], s["знаков_skill"], s["строк_тела"],
                 ("%d зн." % s["знаков_справочника"]) if s["справочник"] else "нет",
                 s["скриптов"], s["проверок"],
                 ("`%s`" % s["пара"]["имя"]) if s["пара"] else "—"))
        a("")
    return "\n".join(L) + "\n"


def _by_section(reg, reading):
    """Разбор пойдёт по нашим разделам, а не по чужим наборам — так и подаём."""
    paired = {s["имя"]: bool(s["пара"]) for s in reg["навыки"]}
    groups = {}
    for rec in reading.values():
        groups.setdefault(rec.get("раздел", "—"), []).append(rec)

    L = ["## По нашим разделам", "",
         "Единица разбора — навык. Парная единица (`X` и `1c-X`) идёт одной",
         "строкой: две версии одного навыка разбираются вместе, сравнением.", ""]
    order = sorted(groups, key=lambda k: (k == "вне раскладки", -len(groups[k]), k))
    for section in order:
        rows = sorted(groups[section], key=lambda r: r["единица"])
        L.append("### %s — %d" % (section, len(rows)))
        L.append("")
        L.append("| Единица | Версий | Суть | Опора |")
        L.append("|---|---|---|---|")
        for r in rows:
            L.append("| `%s` | %s | %s | %s |"
                     % (r["единица"],
                        "две" if paired.get(r["единица"]) else "одна",
                        r["суть"].replace("|", "\\|"),
                        r.get("опора", "")))
        L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ref", default=str(ROOT / "_ref"))
    ap.add_argument("--out-json", default=str(ROOT / "docs" / "reference-registry.json"))
    ap.add_argument("--out-md", default=str(ROOT / "docs" / "reference-registry.md"))
    ap.add_argument("--reading", default=str(ROOT / "docs" / "reference-reading.json"),
                    help="читающий слой; его отсутствие не ошибка")
    args = ap.parse_args()

    reg = build(args.ref)
    reading = read_reading_layer(args.reading)
    Path(args.out_json).write_text(
        json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    Path(args.out_md).write_text(as_markdown(reg, reading), encoding="utf-8", newline="\n")

    print("навыков: %d, в паре: %d (%d пар), различных: %d"
          % (reg["всего_навыков"], reg["навыков_в_паре"],
             reg["навыков_в_паре"] // 2, reg["различных_навыков"]))
    for s in reg["наборы"]:
        print("  %-24s %3d навыков, ревизия %s (%s)"
              % (s["репозиторий"], s["навыков"], s["коммит"], s["дата"]))
    print("записано: %s, %s" % (args.out_json, args.out_md))


if __name__ == "__main__":
    main()
