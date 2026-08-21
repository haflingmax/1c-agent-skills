"""Проверка командной строки 1С:Предприятия до её запуска.

Ловит то, что модель выдумывает чаще всего: несуществующий ключ, ключ не из того
режима, опцию не от той команды, отсутствие обязательного пакетного ключа и
заглушку вместо настоящего пути.

Состав ключей взят из руководства администратора 8.3.27, приложение 7
(140 ключей), и лежит в cli-keys.json рядом с этим файлом.

    python scripts/check-1c-cli.py "1cv8 DESIGNER /F d:/base /LoadCfg new.cf /UpdateDBCfg"
    echo "<команда>" | python scripts/check-1c-cli.py

Код возврата 0 — замечаний нет, 1 — есть. Годится для CI и для вызова из навыка.
"""
import json
import re
import sys
from pathlib import Path

CATALOG = Path(__file__).resolve().parent / "cli-keys.json"

# Режим задаётся вторым словом команды. «общий» подходит любому режиму.
MODE_WORDS = {"DESIGNER", "ENTERPRISE", "CREATEINFOBASE", "CONFIG"}

# Без этого пакетный запуск открывает диалог и висит вечно.
BATCH_REQUIRED = "/DisableStartupDialogs"

# Ключи, которые меняют базу необратимо. Для них проверяем страховку.
DESTRUCTIVE = {"/LoadCfg", "/LoadConfigFromFiles", "/UpdateDBCfg", "/RestoreIB", "/MergeCfg"}

# Заглушки вместо настоящих значений. Команда с такой подстановкой либо не
# запустится, либо отработает не там, поэтому это ошибка, а не замечание.
PLACEHOLDERS = [
    (re.compile(r"8\.\d+\.(?:x+|n+|\?\?)(?![0-9])", re.I),
     "версия платформы не подставлена"),
    (re.compile(r"(?<![A-Za-z0-9])(?:xxx+|yyyy|nnnn)(?![A-Za-z0-9])", re.I),
     "заглушка вместо части пути"),
    (re.compile(r"%[A-Za-z_]\w*%"),
     "переменная окружения в имени файла: %date% зависит от локали и содержит "
     "разделители, имя файла получается непредсказуемым"),
    (re.compile(r"<[^<>]{2,40}>"),
     "угловые скобки из документации оставлены в команде"),
    (re.compile(r"(?<![А-Яа-яЁёA-Za-z])(?:ваш\w*|путь_к|path_to|your)(?![А-Яа-яЁёA-Za-z])", re.I),
     "подстановка словом вместо настоящего пути"),
    (re.compile(r"\.{3,}"),
     "многоточие вместо значения"),
]


def load_catalog():
    if not CATALOG.exists():
        print("нет файла %s" % CATALOG.name)
        raise SystemExit(2)
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def split_args(line):
    """Разбирает строку с учётом кавычек, не ломаясь о пути с пробелами."""
    return [a for a in re.findall(r'"[^"]*"|\S+', line) if a]


def matches_option(arg, option):
    """Опция совпадает точно либо со значением, приклеенным без пробела.

    В документации такие записаны как -Dynamic<Режим>, а на деле пишутся
    -Dynamic- и -Dynamic+. Приклеенное значение не может быть буквенным,
    иначе -Extensions прошло бы за -Extension.
    """
    a, o = arg.lower(), option.lower()
    if a == o:
        return True
    if a.startswith(o):
        tail = arg[len(option):]
        return bool(tail) and not tail[0].isalpha()
    return False


def check(line, catalog):
    keys = catalog["ключи"]
    args = split_args(line)
    problems = []
    notes = []

    if not args:
        return ["пустая команда"], []

    mode = None
    for a in args[1:4]:
        up = a.upper()
        if up in MODE_WORDS:
            mode = up
            break
    if mode is None:
        problems.append(
            "не указан режим запуска: после имени программы ожидается "
            "DESIGNER, ENTERPRISE или CREATEINFOBASE")

    used = []
    for i, a in enumerate(args):
        if not a.startswith("/"):
            continue
        name = a.split(":", 1)[0]
        if name in keys:
            used.append((name, i))
            continue
        # /L<код> и /VL<код> пишутся слитно со значением
        glued = next((k for k in keys
                      if len(k) > 2 and name.startswith(k) and len(name) > len(k)), None)
        if glued:
            used.append((glued, i))
            continue
        near = [k for k in keys if k.lower() == name.lower()]
        if near:
            problems.append("%s — неверный регистр, в документации %s" % (a, near[0]))
            used.append((near[0], i))
        else:
            problems.append("%s — такого ключа нет в документации 8.3.27" % a)

    for name, _ in used:
        km = keys[name].get("mode")
        if mode and km in MODE_WORDS and km != mode:
            problems.append(
                "%s работает в режиме %s, а команда запущена как %s" % (name, km, mode))

    # опции принадлежат ближайшему предшествующему ключу
    owners = {i: name for name, i in used}
    current = None
    for i, a in enumerate(args):
        if i in owners:
            current = owners[i]
            continue
        if not a.startswith("-") or len(a) < 2 or a[1].isdigit():
            continue
        if current is None:
            problems.append("%s — опция указана до первого ключа" % a)
            continue
        allowed = keys[current].get("opts") or []
        if allowed and not any(matches_option(a, o) for o in allowed):
            near = [o for o in allowed if o.lower().startswith(a.lower()[:5])]
            hint = (", возможно " + near[0]) if near else ""
            problems.append("%s не является опцией %s%s" % (a, current, hint))

    # заглушки ищем по всей строке: <каталог базы> разрезается пробелом на два слова
    for pat, why in PLACEHOLDERS:
        m = pat.search(line)
        if m:
            problems.append("«%s» — %s; значение запрашивается у человека, "
                            "а не выдумывается" % (m.group(0), why))

    names = {n for n, _ in used}

    if mode == "DESIGNER" and names and BATCH_REQUIRED not in names:
        notes.append(
            "нет %s — пакетный запуск откроет диалог и остановится" % BATCH_REQUIRED)

    if names & DESTRUCTIVE and "/Out" not in names and "/DumpResult" not in names:
        notes.append(
            "нет /Out и /DumpResult — при сбое не останется ни журнала, ни кода возврата")

    if "/UpdateDBCfg" in names and not any(a.lower().startswith("-dynamic") for a in args):
        notes.append(
            "/UpdateDBCfg без -Dynamic: решение о динамическом обновлении "
            "принимается заранее, а не оставляется платформе")

    if not any(a.startswith("/F") or a.startswith("/S") or a.startswith("/IBName")
               or a.upper() == "CREATEINFOBASE" for a in args):
        problems.append("не задана база: нужен /F, /S или /IBName")

    return problems, notes


def main():
    line = " ".join(sys.argv[1:]).strip()
    if not line:
        line = sys.stdin.read().strip()
    if not line:
        print(__doc__.strip().splitlines()[0])
        return 2

    problems, notes = check(line, load_catalog())

    for p in problems:
        print("[ошибка] %s" % p)
    for n in notes:
        print("[внимание] %s" % n)
    if not problems and not notes:
        print("замечаний нет")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
