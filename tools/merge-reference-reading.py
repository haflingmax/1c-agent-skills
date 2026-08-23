"""Сведение читающего слоя описи референсов (этап РАЗБОР-1а).

Механический слой (`docs/reference-registry.json`) собирается из файлов и
воспроизводится побайтно. Читающий слой — суждение: о чём навык на самом
деле и к какому из наших 16 разделов относится. Воспроизвести его нельзя,
поэтому он живёт отдельным файлом и проходит проверку на входе.

Проверяется то, что можно проверить механически:
  - покрыта ли каждая единица ровно один раз и нет ли лишних;
  - на месте ли обязательные поля;
  - назван ли раздел из списка, а не выдуманный;
  - есть ли опора — цитата с путём и строкой, и ведёт ли путь к живому файлу;
  - для парных единиц — сказано ли, чем версии различаются;
  - не просочился ли вердикт о судьбе объекта.

Последнее — не придирка. Опись обязана прийти к следующему этапу
нейтральной: читатель, который заодно советует, начинает подгонять описание
под свой совет, и то, что он мысленно отверг, описывается тусклее.

Запуск: PYTHONIOENCODING=utf-8 python tools/merge-reference-reading.py <каталог с out-*.json>
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SECTIONS = [
    "1c-code-conventions", "1c-metadata-objects", "1c-managed-forms", "1c-queries",
    "1c-access-rights", "1c-security", "1c-client-server", "1c-extensions",
    "1c-reports-and-layouts", "1c-integrations", "1c-libraries-bsp", "1c-localization",
    "1c-build-and-db", "1c-update-and-support", "1c-quality-gates", "1c-publish-and-operate",
]
OUTSIDE = "вне раскладки"

REQUIRED = ["единица", "суть", "входы_выходы", "раздел", "почему_раздел",
            "опора", "скрипты", "разница_версий", "цитата"]

# Вердикт ловится КОНСТРУКЦИЕЙ совета, а не корнем слова.
#
# Первая редакция искала корни «перенос», «брать», «полезн» — и дала шесть
# ложных срабатываний из шести на живых данных. Все шесть оказались доменным
# языком 1С: «проверка переноса вставок», «переносимые в расширение»,
# «переносит приближённо», «текст запроса без переносов», «брать configSrc
# базы», «не переносит пользовательские данные». Ни одного настоящего совета.
#
# Правило набора здесь то же, что у проверяльщика командной строки:
# запрещать только доказанное. Совет отличается от описания не словом,
# а конструкцией — «стоит», «не нужно», «рекомендую», «полезно для нас».
VERDICT = re.compile(
    r"(?:перенос|брать|взять|бер[её]м)\w*\s+(?:стоит|не\s+нужн\w*|нужн\w*|целиком)"
    r"|(?:стоит|не\s+стоит|нужно|не\s+нужно)\s+(?:перенос|брать|взять)\w*"
    r"|полезн\w*\s+(?:для\s+нас|нам)"
    r"|(?:для\s+нас|нам)\s+(?:полезн|пригод|подойд|не\s+нужн)\w*"
    r"|рекомендую|советую|бесполезн\w*|отвергн\w*",
    re.IGNORECASE)

# Путь в цитате: любое расширение, а не только .md — читатель вправе
# сослаться и на скрипт навыка. Кандидатов может быть несколько: цитируемый
# текст сам нередко упоминает соседние файлы («см. regress.md»), и настоящий
# источник стоит в конце. Поэтому годится, если хоть один кандидат ведёт
# к живому файлу, а не первый попавшийся.
CITE = re.compile(r"[\w./\\-]+\.(?:md|py|ps1|psm1|json|xml|txt|bsl|os|cmd|bat)\b")


def fail(message, code=2):
    sys.stdout.write(message + "\n")
    raise SystemExit(code)


def load_units(registry):
    """Единицы разбора: парные считаются один раз, ведущей стороной."""
    by = {(s["набор"], s["имя"]): s for s in registry["навыки"]}
    units, seen = {}, set()
    for s in registry["навыки"]:
        key = (s["набор"], s["имя"])
        if key in seen:
            continue
        seen.add(key)
        versions = [s]
        if s["пара"]:
            p = by[(s["пара"]["набор"], s["пара"]["имя"])]
            seen.add((p["набор"], p["имя"]))
            versions.append(p)
        units[s["имя"]] = versions
    return units


def citation_text(cite):
    """Цитата плоской строкой, какой бы формы она ни пришла.

    Задание читателям допускало обе: «выдержка … и путь:строка» можно понять
    и как одну строку, и как объект с полями. Пять читателей из восьми поняли
    первым способом, трое — вторым, и оба прочтения верны. Двусмысленность
    в задании — не повод браковать честную работу: приводим к общему виду.
    """
    if isinstance(cite, dict):
        return " ".join(str(v) for v in cite.values())
    return str(cite or "")


def check_record(rec, units, ref_root):
    """Замечания по одной записи. Пустой список — запись годна."""
    out = []
    name = rec.get("единица", "")
    missing = [f for f in REQUIRED if f not in rec]
    if missing:
        out.append("нет полей: %s" % ", ".join(missing))
        return out

    if name not in units:
        out.append("единицы «%s» нет в механическом слое" % name)
        return out

    if not rec["суть"].strip():
        out.append("пустая суть")

    section = rec["раздел"]
    if section not in SECTIONS and section != OUTSIDE:
        out.append("раздел «%s» не из списка и не «%s»" % (section, OUTSIDE))

    cite = citation_text(rec["цитата"])
    if not cite.strip():
        out.append("нет цитаты — утверждение не на что опереть")
    else:
        paths = [m.group(0).replace("\\", "/") for m in CITE.finditer(cite)]
        if not paths:
            out.append("в цитате нет пути к файлу")
        elif not any((ref_root / p).is_file() for p in paths):
            out.append("ни один путь из цитаты не ведёт к файлу: %s" % ", ".join(paths))

    paired = len(units[name]) == 2
    if paired and not rec["разница_версий"].strip():
        out.append("единица парная, а разница версий не названа")
    if not paired and rec["разница_версий"].strip():
        out.append("единица непарная, а разница версий заполнена")

    for field in ("суть", "почему_раздел", "входы_выходы"):
        m = VERDICT.search(rec[field])
        if m:
            out.append("в поле «%s» просочился вердикт: «%s»" % (field, m.group(0)))
    return out


def merge(reading_dir, registry_path, ref_root):
    registry_path = Path(registry_path)
    if not registry_path.is_file():
        fail("[ошибка] нет %s — сначала соберите механический слой:\n"
             "  python tools/build-reference-registry.py" % registry_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    units = load_units(registry)

    reading_dir = Path(reading_dir)
    parts = sorted(reading_dir.glob("out-*.json"))
    if not parts:
        fail("[ошибка] в %s нет ни одного файла out-*.json.\n"
             "Читающий слой собирают агенты-читатели; без их выводов\n"
             "сводить нечего. Пустой файл не записан намеренно." % reading_dir)

    records, problems, seen = [], [], {}
    for part in parts:
        try:
            data = json.loads(part.read_text(encoding="utf-8"))
        except ValueError as e:
            problems.append("%s: не разбирается как JSON: %s" % (part.name, e))
            continue
        if not isinstance(data, list):
            problems.append("%s: ожидался массив, получено %s" % (part.name, type(data).__name__))
            continue
        for rec in data:
            name = rec.get("единица", "?")
            if name in seen:
                problems.append("единица «%s» описана дважды: %s и %s"
                                % (name, seen[name], part.name))
                continue
            seen[name] = part.name
            for note in check_record(rec, units, ref_root):
                problems.append("%s / %s: %s" % (part.name, name, note))
            records.append(rec)

    uncovered = sorted(set(units) - set(seen))
    if uncovered:
        problems.append("не описаны %d единиц: %s"
                        % (len(uncovered), ", ".join(uncovered[:10])
                           + (" …" if len(uncovered) > 10 else "")))

    records.sort(key=lambda r: r.get("единица", ""))
    return {
        "что_это": "Читающий слой описи референсов. Суждение, а не выгрузка: "
                   "воспроизвести перезапуском нельзя, поэтому проверяется на входе.",
        "единиц": len(records),
        "вне_раскладки": sum(1 for r in records if r.get("раздел") == OUTSIDE),
        "по_разделам": {s: sum(1 for r in records if r.get("раздел") == s)
                        for s in SECTIONS
                        if any(r.get("раздел") == s for r in records)},
        "записи": records,
    }, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reading_dir", help="каталог с out-*.json от читателей")
    ap.add_argument("--registry", default=str(ROOT / "docs" / "reference-registry.json"))
    ap.add_argument("--ref", default=str(ROOT / "_ref"))
    ap.add_argument("--out", default=str(ROOT / "docs" / "reference-reading.json"))
    ap.add_argument("--force", action="store_true",
                    help="записать несмотря на замечания (замечания всё равно печатаются)")
    args = ap.parse_args()

    reading, problems = merge(args.reading_dir, args.registry, Path(args.ref))

    for p in problems:
        print("[замечание] %s" % p)

    if problems and not args.force:
        print("\nзамечаний: %d. Файл не записан. Исправьте выводы читателей "
              "или запустите с --force, если замечания разобраны." % len(problems))
        raise SystemExit(1)

    Path(args.out).write_text(
        json.dumps(reading, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    print("единиц описано: %d, вне раскладки: %d, замечаний: %d"
          % (reading["единиц"], reading["вне_раскладки"], len(problems)))
    for section, n in sorted(reading["по_разделам"].items(), key=lambda kv: -kv[1]):
        print("  %-24s %3d" % (section, n))
    print("записано: %s" % args.out)


if __name__ == "__main__":
    main()
