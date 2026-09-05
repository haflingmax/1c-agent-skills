"""Чтение журнала приёмки: ответы агентов из `run-acceptance.ps1` в один файл.

    python tools/read-acceptance.py D:/tmp/1c-acceptance/run1-kilo-9to20
    python tools/read-acceptance.py <каталог> --пара 9 --полярность Neg

Приёмку нельзя свести к числу. Скрипт `run-acceptance.ps1` пишет в journal
поле `questionsRaw` — счёт знаков «?» — и сам предупреждает, что мера это
негодная: вопросительный знак ловит тернарный оператор `?(Условие, Да, Нет)`
и `<?xml ?>`. На первом же прогоне 05.09.2026 так и вышло: у прошедшего Pos
стояло `questionsRaw = 1`, и единица была тернарным оператором внутри
выданного кода.

Поэтому прибор здесь не судит, а **достаёт текст**: ответ агента, список
поднятых навыков и признак загрузки — чтобы человек прочитал и решил.
Логи Kilo приходят в UTF-16 и JSON Lines по строке на событие; вручную
это не читается.

Что печатается по каждому прогону:

  * пара, полярность, среда;
  * поднялся ли навык и какие именно (поле `skills` журнала);
  * последний текстовый ответ агента целиком.

С `--кратко` печатается только шапка — так видно раскладку всего прогона
на одном экране.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

# Про эту преамбулу см. check-sources.py: перенаправленный вывод берёт ANSI
# системы, и первый же знак вне cp1251 роняет отчёт трассировкой.
if not os.environ.get("PYTHONIOENCODING"):
    for _поток in (sys.stdout, sys.stderr):
        try:
            _поток.reconfigure(encoding="utf-8", errors=_поток.errors)
        except (AttributeError, ValueError):
            pass


def события(каталог):
    """Записи progress.jsonl. Файл пишется PowerShell-ом и идёт с BOM."""
    файл = Path(каталог) / "progress.jsonl"
    if not файл.is_file():
        raise SystemExit("нет журнала: %s" % файл)
    out = []
    for строка in файл.read_text(encoding="utf-8-sig").splitlines():
        строка = строка.strip()
        if строка.startswith("{"):
            out.append(json.loads(строка))
    return out


СБОЙ = "[СРЕДА СОРВАЛАСЬ]"


def ответ(путь):
    """Последний текстовый ответ агента из run.log.

    Kilo пишет UTF-16 с BOM; каждая строка — событие, и текст лежит
    в part.text у частей типа text. Берётся последняя: предыдущие —
    промежуточные рассуждения и вывод инструментов.
    """
    п = Path(путь)
    if not п.is_file():
        return None
    сырое = п.read_bytes()
    if сырое[:2] in (b"\xff\xfe", b"\xfe\xff"):
        текст = сырое.decode("utf-16")
    else:
        текст = сырое.decode("utf-8-sig", errors="replace")
    куски, сбой = [], None
    for строка in текст.splitlines():
        строка = строка.strip()
        if not строка.startswith("{"):
            continue
        try:
            о = json.loads(строка)
        except ValueError:
            continue
        # Среда падает молча для вызывающего: kilo.exe возвращает 0, скрипт
        # прогона пишет run-done, и прогон выглядит состоявшимся при пустом
        # ответе. Поймано 05.09.2026 на паре 15 Neg: 35 шагов, 37 вызовов
        # инструментов и «Invalid prompt: The messages do not match the
        # ModelMessage[] schema» в конце. Сорвавшийся прогон обязан быть
        # виден как сорвавшийся, а не как ответ длиной ноль.
        if о.get("type") == "error":
            данные = (о.get("error") or {}).get("data") or {}
            сбой = данные.get("message") or (о.get("error") or {}).get("name")
            continue
        часть = о.get("part") or {}
        if часть.get("type") == "text" and часть.get("text"):
            куски.append(часть["text"])
    if куски:
        return куски[-1]
    return (СБОЙ + " " + сбой) if сбой else None


def main():
    р = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    р.add_argument("каталог")
    р.add_argument("--пара", type=int, action="append")
    р.add_argument("--полярность", choices=["Pos", "Neg"])
    р.add_argument("--кратко", action="store_true")
    а = р.parse_args()

    прогонов = сорвалось = без_навыка = 0
    for о in события(а.каталог):
        вид = о.get("event")
        if вид not in ("run-done", "run-timeout", "run-error", "skip"):
            continue
        if а.пара and о.get("pair") not in а.пара:
            continue
        if а.полярность and о.get("pol") != а.полярность:
            continue
        шапка = "=== пара %-3s %-3s  %s" % (о.get("pair"), о.get("pol"),
                                            о.get("env"))
        if вид != "run-done":
            сорвалось += 1
            print(шапка + "  — %s %s" % (вид, о.get("reason", "")))
            continue
        т = ответ(о.get("log", ""))
        # Прогон, у которого среда упала, считается сорвавшимся, а не
        # состоявшимся: иначе сводка врёт в сторону благополучия — ровно
        # ту ошибку набор ловит у своих приборов третий раз.
        упал = bool(т) and т.startswith(СБОЙ)
        if упал:
            сорвалось += 1
            print(шапка + "  — среда сорвалась")
            if not а.кратко:
                print("    " + т[len(СБОЙ):].strip())
                print()
            continue
        прогонов += 1
        поднят = bool(о.get("skill"))
        if not поднят:
            без_навыка += 1
        print(шапка + "  навык: %s  [%s]"
              % ("да" if поднят else "НЕТ", о.get("skills") or "—"))
        if а.кратко:
            continue
        print(т if т else "    (ответа в журнале нет)")
        print()

    print("прогонов прочитано: %d, без поднятия навыка: %d, сорвалось: %d"
          % (прогонов, без_навыка, сорвалось))
    if not прогонов and not сорвалось:
        print("ВНИМАНИЕ: вход пуст — прибор ничего не смотрел, и ноль находок "
              "об этом не говорит")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
