"""Сведение перечня тем по разделам (этап РАЗБОР-2а).

Опись сказала, что есть у чужих наборов. Этот этап отвечает на другой вопрос:
**что обязан покрыть наш набор**. Выход — перечень тем по каждому из 15
разделов плюс разбор единиц, не легших ни в один.

Тема здесь значит «набор обязан уметь отвечать на это», а не «взять оттуда
текст»: чужой материал не переносится вовсе (решение 16 общего плана).

Правило вердикта и разбор цитаты берутся из `merge-reference-reading.py`,
а не переписываются сюда. Оба дались двумя раундами правок на живых данных —
на доменном слове «перенос» и на цитате, ссылающейся на скрипт. Третья копия
разошлась бы с первыми двумя к следующему проходу.

Запуск: PYTHONIOENCODING=utf-8 python tools/merge-coverage-backlog.py <каталог с out-*.json>
"""
import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

# Вывод этих скриптов — кириллица и знаки «», «—», «→». Пока stdout остаётся
# окном консоли, беды нет: Python 3.14 на Windows пишет туда через WriteConsoleW
# и отдаёт utf-8 при любой кодовой странице — проверено запуском 25.08.2026 под
# chcp 866, 1251 и 65001, во всех трёх sys.stdout.encoding == 'utf-8'.
#
# Ломается ПЕРЕНАПРАВЛЕНИЕ: когда вывод уходит в файл или в трубу, Python берёт
# ANSI-кодировку системы (здесь cp1251), и первый же знак вне неё роняет скрипт
# трассировкой вместо отчёта. Так падал check-1c-cli.py, отгружаемый внутри
# навыка, и так its-search.py не мог отдать даже --help.
#
# Две оговорки, каждая из-за собственной ошибки первой редакции:
#   errors= передаём прежний — reconfigure(encoding=...) молча ставит strict,
#   а интерпретатор держит на stdout surrogateescape и на stderr
#   backslashreplace нарочно, чтобы печать имени файла с одиночным суррогатом
#   (обычное дело в Windows) не роняла сам вывод;
#   при заданной PYTHONIOENCODING не трогаем ничего — иначе у человека
#   не остаётся способа задать кодировку под своего потребителя вывода.
if not os.environ.get("PYTHONIOENCODING"):
    for _поток in (sys.stdout, sys.stderr):
        try:
            _поток.reconfigure(encoding="utf-8", errors=_поток.errors)
        except (AttributeError, ValueError):
            pass


ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "merge_reference_reading", ROOT / "tools" / "merge-reference-reading.py")
_mrr = importlib.util.module_from_spec(_spec)
sys.modules["merge_reference_reading"] = _mrr
_spec.loader.exec_module(_mrr)

SECTIONS, RETIRED = _mrr.SECTIONS, _mrr.RETIRED
VERDICT, CITE = _mrr.VERDICT, _mrr.CITE
citation_text = _mrr.citation_text

OUT_OF_SCOPE = ["конфигурационная специфика", "БСП", "не 8.3", "не про 1С",
                "дублирует другую единицу"]
NOT_PLACED = ["вне охвата по правилу", "не про 1С",
              "раскладке не хватает раздела", "ложится в существующий"]


def fail(message, code=2):
    sys.stdout.write(message + "\n")
    raise SystemExit(code)


def cited_paths(value):
    return [m.group(0).replace("\\", "/") for m in CITE.finditer(citation_text(value))]


def check_support(value, ref_root, where):
    """Опора обязана вести к живому файлу. Утверждение без опоры не считается."""
    paths = cited_paths(value)
    if not paths:
        return ["%s: в опоре нет пути к файлу" % where]
    if not any((ref_root / p).is_file() for p in paths):
        return ["%s: ни один путь из опоры не ведёт к файлу: %s" % (where, ", ".join(paths))]
    return []


def check_section_file(data, expected_units, ref_root):
    """Замечания по выходу одного раздела."""
    out = []
    section = data.get("раздел", "")
    if section not in SECTIONS:
        out.append("раздел «%s» не из пятнадцати" % section)

    units = data.get("единицы")
    topics = data.get("темы")
    if not isinstance(units, list) or not isinstance(topics, list):
        return out + ["ожидались списки «единицы» и «темы»"]

    seen = {}
    for u in units:
        name = u.get("единица", "?")
        if name in seen:
            out.append("единица «%s» разобрана дважды" % name)
            continue
        seen[name] = u
        if "в_охвате" not in u:
            out.append("%s: нет поля «в_охвате»" % name)
            continue
        in_scope = bool(u["в_охвате"])
        why = str(u.get("почему_нет", "")).strip()
        if in_scope and why:
            out.append("%s: в охвате, но заполнено «почему_нет»" % name)
        if not in_scope and why not in OUT_OF_SCOPE:
            out.append("%s: причина «%s» не из перечня: %s" % (name, why, ", ".join(OUT_OF_SCOPE)))
        own = u.get("темы_единицы") or []
        if not in_scope and own:
            out.append("%s: вне охвата, но названы темы" % name)

    missing = sorted(set(expected_units) - set(seen))
    extra = sorted(set(seen) - set(expected_units))
    if missing:
        out.append("не разобраны %d единиц: %s" % (len(missing), ", ".join(missing[:8])))
    if extra:
        out.append("разобраны единицы не из этого раздела: %s" % ", ".join(extra[:8]))

    names = set()
    for t in topics:
        name = str(t.get("тема", "")).strip()
        if not name:
            out.append("тема без имени")
            continue
        if name in names:
            out.append("тема «%s» названа дважды — сведение повторов не доведено" % name)
        names.add(name)
        if not str(t.get("о_чём", "")).strip():
            out.append("тема «%s»: пустое «о_чём»" % name)
        src = t.get("откуда") or []
        if not src:
            out.append("тема «%s»: не сказано, из каких единиц выведена" % name)
        for s in src:
            if s not in seen:
                out.append("тема «%s»: единицы «%s» нет в этом разделе" % (name, s))
        out += check_support(t.get("опора", ""), ref_root, "тема «%s»" % name)
        for field in ("тема", "о_чём"):
            m = VERDICT.search(str(t.get(field, "")))
            if m:
                out.append("тема «%s»: в поле «%s» просочился вердикт: «%s»"
                           % (name, field, m.group(0)))

    for u in units:
        for t in (u.get("темы_единицы") or []):
            if t not in names:
                out.append("%s: названа тема «%s», которой нет в перечне"
                           % (u.get("единица", "?"), t))
    return out


def check_outside_file(data, expected_units, ref_root):
    """Замечания по выходу «вне раскладки». Вопрос там другой — жмёт ли раскладка."""
    out = []
    units = data.get("единицы")
    if not isinstance(units, list):
        return ["ожидался список «единицы»"]

    seen = set()
    for u in units:
        name = u.get("единица", "?")
        if name in seen:
            out.append("единица «%s» разобрана дважды" % name)
        seen.add(name)
        why = str(u.get("почему_не_легла", "")).strip()
        if why not in NOT_PLACED:
            out.append("%s: причина «%s» не из перечня: %s" % (name, why, ", ".join(NOT_PLACED)))
        section = str(u.get("раздел", "")).strip()
        if why == "ложится в существующий":
            if section not in SECTIONS:
                out.append("%s: сказано «ложится», но раздел «%s» не из пятнадцати"
                           % (name, section))
        elif section:
            out.append("%s: раздел заполнен, хотя причина не «ложится в существующий»" % name)
        out += check_support(u.get("опора", ""), ref_root, name)

    missing = sorted(set(expected_units) - seen)
    if missing:
        out.append("не разобраны %d единиц: %s" % (len(missing), ", ".join(missing[:8])))

    for p in (data.get("предложения") or []):
        title = str(p.get("предложение", "")).strip()
        if not title:
            out.append("предложение без имени")
            continue
        if not str(p.get("основание", "")).strip():
            out.append("предложение «%s»: нет основания" % title)
        if not str(p.get("против", "")).strip():
            out.append("предложение «%s»: не названо, что говорит против. "
                       "Предложение без возражения владелец взвесить не сможет" % title)
    return out


def expected_by_file(triage_dir):
    """Что каждому агенту давали на вход — по этому и сверяется полнота."""
    out = {}
    for p in sorted(Path(triage_dir).glob("*.json")):
        if p.name.startswith("out-") or p.name.startswith("brief"):
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        if "записи" not in d:
            continue
        out[p.stem] = [r["единица"] for r in d["записи"]]
    return out


def merge(triage_dir, ref_root):
    triage_dir, ref_root = Path(triage_dir), Path(ref_root)
    expected = expected_by_file(triage_dir)
    if not expected:
        fail("[ошибка] в %s нет входных файлов разделов. Опись раскладывают\n"
             "по разделам до запуска агентов; сводить нечего." % triage_dir)

    parts = sorted(triage_dir.glob("out-*.json"))
    if not parts:
        fail("[ошибка] в %s нет ни одного файла out-*.json.\n"
             "Перечень тем собирают агенты-сортировщики; без их выводов\n"
             "сводить нечего. Пустой файл не записан намеренно." % triage_dir)

    разделы, вне, предложения, problems = [], [], [], []
    covered = set()
    for part in parts:
        stem = part.stem[4:]
        try:
            data = json.loads(part.read_text(encoding="utf-8"))
        except ValueError as e:
            problems.append("%s: не разбирается как JSON: %s" % (part.name, e))
            continue
        exp = expected.get(stem)
        if exp is None:
            problems.append("%s: нет входного файла %s.json — с чем сверять полноту?"
                            % (part.name, stem))
            exp = []
        covered.add(stem)
        if stem == "outside":
            for n in check_outside_file(data, exp, ref_root):
                problems.append("%s: %s" % (part.name, n))
            вне.extend(data.get("единицы") or [])
            предложения.extend(data.get("предложения") or [])
        else:
            for n in check_section_file(data, exp, ref_root):
                problems.append("%s: %s" % (part.name, n))
            разделы.append(data)

    for stem in sorted(set(expected) - covered):
        problems.append("раздел %s не разобран вовсе — нет out-%s.json" % (stem, stem))

    разделы.sort(key=lambda d: -len(d.get("темы") or []))
    всего_тем = sum(len(d.get("темы") or []) for d in разделы)
    отсеяно = {}
    for d in разделы:
        for u in d.get("единицы") or []:
            if not u.get("в_охвате"):
                отсеяно[u.get("почему_нет", "?")] = отсеяно.get(u.get("почему_нет", "?"), 0) + 1

    return {
        "что_это": "Перечень тем, которые обязан покрыть набор, по 15 разделам. "
                   "Выведен из описи референсов; чужой материал не переносится.",
        "всего_тем": всего_тем,
        "разделов_разобрано": len(разделы),
        "отсеяно_из_разделов": отсеяно,
        "разделы": разделы,
        "вне_раскладки": вне,
        "предложения_по_раскладке": предложения,
    }, problems


def as_markdown(b):
    L = []
    a = L.append
    a("# Что обязан покрыть набор (РАЗБОР-2а)")
    a("")
    a("Порождается `tools/merge-coverage-backlog.py` из выводов агентов-сортировщиков.")
    a("")
    a("Тема здесь значит «набор обязан уметь отвечать на это», а **не** «взять текст")
    a("из референса»: чужой материал не переносится вовсе (решение 16).")
    a("")
    a("**Перечень неполон по построению.** Он выведен из того, что заметили два чужих")
    a("набора, а не из официальной документации. Тексты системы стандартов (318) и")
    a("методических материалов (605) на момент составления не выгружены, поэтому")
    a("разделы, стоящие на них, представлены обрывочно. Полнота даётся сверкой с ИТС —")
    a("это следующий этап, а не этот.")
    a("")
    a("Тем всего: **%d** в %d разделах." % (b["всего_тем"], b["разделов_разобрано"]))
    if b["отсеяно_из_разделов"]:
        a("")
        a("Отсеяно из разделов правилами охвата: "
          + ", ".join("%s — %d" % (k, v) for k, v in sorted(b["отсеяно_из_разделов"].items())))
    a("")

    for d in b["разделы"]:
        topics = d.get("темы") or []
        a("## %s — %d тем" % (d.get("раздел", "?"), len(topics)))
        a("")
        for t in topics:
            a("### %s" % t.get("тема", "?"))
            a("")
            a(t.get("о_чём", ""))
            a("")
            a("*Выведена из: %s*" % ", ".join("`%s`" % s for s in (t.get("откуда") or [])))
            a("")
        for note in (d.get("замечено_сверх") or []):
            a("> **Замечено сверх описи.** %s" % note)
            a("")

    if b["вне_раскладки"]:
        a("## Единицы вне раскладки — %d" % len(b["вне_раскладки"]))
        a("")
        a("| Единица | Почему не легла | Раздел | Пояснение |")
        a("|---|---|---|---|")
        for u in b["вне_раскладки"]:
            a("| `%s` | %s | %s | %s |"
              % (u.get("единица", "?"), u.get("почему_не_легла", ""),
                 u.get("раздел", "") or "—",
                 str(u.get("пояснение", "")).replace("|", "\\|")))
        a("")

    if b["предложения_по_раскладке"]:
        a("## Предложения по раскладке")
        a("")
        a("Материал для решения, а не решение. У каждого названо возражение —")
        a("предложение без него владелец взвесить не сможет.")
        a("")
        for p in b["предложения_по_раскладке"]:
            a("### %s" % p.get("предложение", "?"))
            a("")
            a("**Основание.** %s" % p.get("основание", ""))
            a("")
            a("**Против.** %s" % p.get("против", ""))
            a("")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("triage_dir")
    ap.add_argument("--ref", default=str(ROOT / "_ref"))
    ap.add_argument("--out-json", default=str(ROOT / "docs" / "coverage-backlog.json"))
    ap.add_argument("--out-md", default=str(ROOT / "docs" / "coverage-backlog.md"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    backlog, problems = merge(args.triage_dir, args.ref)
    for p in problems:
        print("[замечание] %s" % p)
    if problems and not args.force:
        print("\nзамечаний: %d. Файл не записан. Исправьте выводы сортировщиков "
              "или запустите с --force, если замечания разобраны." % len(problems))
        raise SystemExit(1)

    Path(args.out_json).write_text(
        json.dumps(backlog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    Path(args.out_md).write_text(as_markdown(backlog), encoding="utf-8", newline="\n")
    print("тем: %d в %d разделах, вне раскладки: %d, предложений: %d, замечаний: %d"
          % (backlog["всего_тем"], backlog["разделов_разобрано"],
             len(backlog["вне_раскладки"]), len(backlog["предложения_по_раскладке"]),
             len(problems)))
    for d in backlog["разделы"]:
        print("  %-24s %3d" % (d.get("раздел", "?"), len(d.get("темы") or [])))
    print("записано: %s, %s" % (args.out_json, args.out_md))


if __name__ == "__main__":
    main()
