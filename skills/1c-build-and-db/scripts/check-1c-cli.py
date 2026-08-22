"""Проверка командной строки 1С:Предприятия до её запуска.

Ловит то, что модель выдумывает чаще всего: несуществующий ключ, ключ не из того
режима, опцию не от той команды, отсутствие обязательного пакетного ключа и
заглушку вместо настоящего пути.

Останавливает работу только то, про что запуском показано, что платформа этого
не делает, — см. docs/evidence/2026-08-22-blocking-rules.md. Остальное уходит в
предупреждения: у них ненулевой смысл и нулевой код возврата. Чужой инструмент
(ibcmd, rac, ras) скрипт не судит вовсе.

Выдуманный ключ ловится запретом, только если он не начинается с одного из
двенадцати слитных (/L, /P, /N, /O, /WSA и прочие). Начинается — сомнение
называется предупреждением: /Lru законен, /LoadCfgFromFile выдуман, и различить
их механически нельзя.

Состав ключей взят из руководства администратора 8.3.27, приложение 7
(140 ключей), и лежит в cli-keys.json рядом с этим файлом.

    python scripts/check-1c-cli.py "1cv8 DESIGNER /F d:/base /LoadCfg new.cf /UpdateDBCfg"
    echo "<команда>" | python scripts/check-1c-cli.py

Код возврата 1 — есть [ошибка]; 0 — запускать можно, даже если есть [внимание].
Годится для CI и для вызова из навыка.
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

# Ключи раздела 7.3.1, каждый из которых задаёт базу. /IBConnectionString здесь
# наравне с остальными: проверено запуском 22.08.2026 —
# DESIGNER /IBConnectionString "File=D:/1C/base/trade;" /DumpCfg создал файл,
# побайтно того же размера, что и выгрузка через /F.
BASE_KEYS = {"/F", "/S", "/IBName", "/IBConnectionString"}

# Ключи, которые меняют базу необратимо. Для них проверяем страховку.
DESTRUCTIVE = {"/LoadCfg", "/LoadConfigFromFiles", "/UpdateDBCfg", "/RestoreIB", "/MergeCfg"}

# Заглушки вместо настоящих значений. Команда с такой подстановкой либо не
# запустится, либо отработает не там, поэтому это ошибка, а не замечание.
PLACEHOLDERS = [
    (re.compile(r"8\.\d+\.(?:x+|n+|\?\?)(?![0-9])", re.I),
     "версия платформы не подставлена"),
    (re.compile(r"(?<![A-Za-z0-9])(?:xxx+|yyyy|nnnn)(?![A-Za-z0-9])", re.I),
     "заглушка вместо части пути"),
    (re.compile(r"<[^<>]{2,40}>"),
     "угловые скобки из документации оставлены в команде"),
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


def known_key(name, keys):
    """Возвращает каноническое имя ключа или None.

    Регистр не важен: платформа регистронезависима, проверено запуском —
    /dumpcfg отработал и создал файл. Значение допускается приклеенным только
    у ключей с признаком glued (их 12, например /L<код языка>). Для остальных
    совпадение по началу имени запрещено: иначе выдуманный /DumpCfgToFile
    молча засчитывается за /DumpCfg.

    Среди glued-ключей берётся самое длинное совпадение, а не первое: /O и
    /OIDA оба glued, и /OIDAOff обязан разрешиться в /OIDA, а не в /O.

    Совпадение по слитному префиксу — не то же самое, что точное. Вызывающая
    сторона обязана их различать: /Lru законен, а /LoadCfgFromFile выдуман, и
    оба разрешаются в /L. Отличить их механически нельзя, поэтому здесь
    возвращается имя, а разговор про сомнение ведёт check().
    """
    low = name.lower()
    for k in keys:
        if k.lower() == low:
            return k
    candidates = [k for k, info in keys.items()
                  if info.get("glued") and len(low) > len(k) and low.startswith(k.lower())]
    return max(candidates, key=len) if candidates else None


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

    tool = Path(args[0].strip('"')).name.lower()
    if not tool.startswith("1cv8"):
        # Не приговор команде, а граница компетенции: замечание с кодом возврата 0.
        # Иначе проверяльщик запрещал бы ibcmd, который рекомендует наш же рецепт
        # (references/load-configuration.md, шаг 3).
        return [], ["%s вне компетенции проверяльщика: он знает только команды 1cv8. "
                    "Состав ключей ibcmd, rac и ras сверяется по документации вручную"
                    % args[0]]

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
        canon = known_key(name, keys)
        if canon:
            used.append((canon, i))
            if canon.lower() != name.lower():
                # Разрешено слитным префиксом, а не точным совпадением. Молча
                # пропускать нельзя: так проходят выдуманные /LoadCfgFromFile,
                # /Publish, /NewConfiguration, /OptimizeDatabase,
                # /WSAuthentication — все начинаются со слитного ключа.
                # Блокировать тоже нельзя: /Lru и /Padmin устроены точно так же
                # и работают (проверено запуском: /Lru + /DumpCfg создал файл).
                # Остаётся назвать сомнение вслух, с нулевым кодом возврата.
                notes.append(
                    "%s — точно такого ключа в документации 8.3.27 нет; разобран "
                    "как %s со значением «%s». Если имелся в виду другой ключ, "
                    "он выдуман" % (a, canon, name[len(canon):]))
        else:
            problems.append("%s — такого ключа нет в документации 8.3.27" % a)

    for name, _ in used:
        km = keys[name].get("mode")
        if not (mode and km in MODE_WORDS and km != mode):
            continue
        where = "%s работает в режиме %s, а команда запущена как %s" % (name, km, mode)
        if km == "DESIGNER":
            # Проверено запуском: ENTERPRISE /F <база> /LoadCfg <файл> не грузит
            # ничего — платформа открывает сеанс и не возвращает управление
            # (убит по таймауту 60 с), журнал пуст, /DumpResult не создан.
            problems.append(where + ": пакетную операцию конфигуратора вне режима "
                                    "DESIGNER выполнять некому — платформа открывает "
                                    "сеанс и не завершается")
        else:
            # Обратное направление запуском опровергнуто: DESIGNER /F <база>
            # /UsePrivilegedMode /DumpCfg отработал, файл создан и совпал по
            # размеру с обычной выгрузкой. Блокировать работающее нельзя.
            notes.append(where + "; в пакетном запуске платформа такой ключ приняла "
                                 "и операцию выполнила — проверь, нужен ли он здесь")

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
            notes.append("%s — опция указана до первого ключа" % a)
            continue
        allowed = keys[current].get("opts") or []
        if allowed and not any(matches_option(a, o) for o in allowed):
            near = [o for o in allowed if o.lower().startswith(a.lower()[:5])]
            hint = (", возможно " + near[0]) if near else ""
            # Не запрет: проверено запуском, что чужая опция команду не ломает —
            # DESIGNER /F <база> /DumpCfg <файл> -Format Hierarchical отработал,
            # файл создан и побайтно того же размера, что и без опции.
            notes.append("%s не является опцией %s%s" % (a, current, hint))

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

    # Сверяемся с каноническими именами из used, а не с началом строки: иначе
    # /f строчными и /IBConnectionString считаются незаданной базой. Блокировка
    # доказана запуском: DESIGNER /DumpCfg <файл> без базы даёт код 1,
    # «Неопределена информационная база», файла нет.
    if not (names & BASE_KEYS) and mode != "CREATEINFOBASE":
        problems.append(
            "не задана база: нужен /F, /S, /IBName или /IBConnectionString")

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
