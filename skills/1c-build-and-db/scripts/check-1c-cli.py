"""Проверка командной строки 1С:Предприятия до её запуска.

Ловит то, что модель выдумывает чаще всего: несуществующий ключ, ключ не из того
режима, опцию не от той команды, отсутствие обязательного пакетного ключа и
заглушку вместо настоящего пути.

Останавливает работу только то, про что запуском показано, что платформа этого
не делает, — см. docs/evidence/2026-08-22-blocking-rules.md. Остальное уходит в
предупреждения: у них ненулевой смысл и нулевой код возврата. Чужой инструмент
(ibcmd, rac, ras) скрипт не судит вовсе.

Разбор имени ключа моделирует платформу, а не только двенадцать слитных
(/L, /P, /N, /O, /WSA и прочие) — но и не «самое длинное совпадение среди
ВСЕХ ключей»: такая формула сама оказалась неверна (Н-02, повторное ревью)
и заблокировала бы законный /PRoxy2024 (→ /Proxy длиннее, чем /P, но
платформа проверено запуском резолвит его в /P + значение «Roxy2024» —
та же ошибка аутентификации, что и у контрольного /Padmin123). Настоящая
модель (выведена шестью живыми прогонами 2026-08-23, см.
docs/evidence/2026-08-22-blocking-rules.md): длинный ключ участвует в
совпадении, только если его аргумент по документации — «голое» позиционное
значение (`<имя файла>` и подобное, без именованных под-ключей). Тогда хвост
токена, не вошедший в совпадение, платформа принимает за это значение и
отправляет не туда (/DumpCfgToFile → /DumpCfg, /OutBase → /Out — оба
проверены запуском: операция выполняется, но не в тот файл) или в никуда
(/LoadCfgFromFile → /LoadCfg — «Файл не обнаружен»). Если длинному ключу
для распознавания нужен отдельный именованный под-ключ (/Proxy: `-PSrv
<адрес> -PPort <порт>`) или он вовсе не берёт аргумента (/NoProxy: пустой
`arg`) — глued-хвост эту форму не удовлетворяет, и платформа откатывается
к короткому slitному ключу (/P, /N) с хвостом как обычным значением.

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
# CONFIG сюда не входит (М-14): раздел 7.3.3 руководства администратора
# называет его, но только как замену, которую платформа делает САМА для
# запуска настоящего 1С:Предприятия 8.0 через /AppAutoCheckVersion — это
# не документированный режим запуска 8.3.27, а внутренний механизм для
# другого исполняемого файла. Ни один ключ каталога не привязан к нему,
# в тексте ошибки он не назван; включать его в MODE_WORDS означало бы
# молча признавать «CONFIG» указанием режима там, где документация 8.3.27
# такого режима не знает вовсе.
MODE_WORDS = {"DESIGNER", "ENTERPRISE", "CREATEINFOBASE"}

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


def absorbs_glued_tail(info):
    """Может ли ключ принять хвост токена как своё значение (glued или нет).

    Н-02, повторное ревью: «самое длинное совпадение среди ВСЕХ ключей» —
    неверная модель, заблокировала бы законный /PRoxy2024 (см. модуль
    docstring). Настоящий критерий — форма документированного аргумента
    ключа (`arg` в cli-keys.json), а не наличие признака glued:

    - `glued=True` (/L, /P, /N, /O и восемь других) — по определению берёт
      значение слитно. Участвует всегда.
    - `glued=False`, но `arg` начинается с «голого» `<значение>» без
      именованного под-ключа (/LoadCfg: `<имя cf/cfe файла> [...]`;
      /DumpCfg — так же; /Out: `<имя файла> [-NoTruncate]`) — платформа
      способна принять остаток токена ЗА это значение. Проверено запуском
      трижды: /LoadCfgFromFile → /LoadCfg + «FromFile» (файл не найден),
      /DumpCfgToFile → /DumpCfg + «ToFile» (выгрузка ушла не в тот файл),
      /OutBase → /Out + «Base» (лог ушёл не в тот файл, DumpCfg при этом
      честно отработал, код 0) — во всех трёх операция либо проваливается,
      либо тихо портит результат.
    - `glued=False` и `arg` требует именованный под-ключ первым делом
      (/Proxy: `-PSrv <адрес> -PPort <порт> ...`) или вовсе пуст (/NoProxy:
      `""`) — глued-хвост эту форму не удовлетворяет, ключ НЕ участвует.
      Проверено запуском дважды: /PRoxy2024 после /N Admin даёт код 1,
      «Пользователь ИБ не идентифицирован» — ровно ту же ошибку, что и
      контрольный /Padmin123, то есть платформа взяла /P, а не /Proxy;
      /NoProxyUser даёт ту же ошибку — платформа взяла /N (у /NoProxy arg
      пуст, ему нечем принять «User»). И отдельно: /Proxy с настоящими
      -PSrv/-PPort прошёл штатно, код 0 — ключ не сломан, он просто не
      достижим слитным хвостом.
    """
    if info.get("glued"):
        return True
    arg = (info.get("arg") or "").strip()
    return arg.startswith("<")


def known_key(name, keys):
    """Возвращает каноническое имя ключа или None.

    Регистр не важен: платформа регистронезависима, проверено запуском —
    /dumpcfg отработал и создал файл.

    Совпадение по префиксу ищется среди ключей, которые способны принять
    хвост как значение (см. absorbs_glued_tail) — это не только двенадцать
    glued, но и не любой ключ каталога: /Proxy и /NoProxy в этот список не
    входят, хотя оба длиннее /P и /N (см. docstring модуля, Н-02).

    Среди подходящих кандидатов берётся самое длинное совпадение, а не
    первое: /O и /OIDA оба подходят /OIDAOff, и результат обязан быть
    /OIDA, а не /O; /LoadCfg длиннее /L и оба подходят /LoadCfgFromFile —
    результат /LoadCfg.

    Совпадение по префиксу — не то же самое, что точное. Вызывающая сторона
    обязана различать их дальше по признаку glued резолвнутого ключа: у /L
    (→ /Lru) хвост — легитимное слитное значение, у /LoadCfg (→
    /LoadCfgFromFile) хвост — позиционный аргумент, который платформа сама
    отправляет не туда. Здесь возвращается только имя; что означает хвост,
    решает check().
    """
    low = name.lower()
    for k in keys:
        if k.lower() == low:
            return k
    candidates = [k for k, info in keys.items()
                  if absorbs_glued_tail(info) and len(low) > len(k) and low.startswith(k.lower())]
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
        if canon is None:
            problems.append("%s — такого ключа нет в документации 8.3.27" % a)
            continue
        if canon.lower() == name.lower():
            used.append((canon, i))
            continue
        # Разрешено префиксом, а не точным совпадением — Н-02: платформа
        # берёт самое длинное совпадение среди ключей, способных принять
        # хвост (absorbs_glued_tail), и решает по-своему, куда его девать.
        # Признак glued резолвнутого ключа говорит, куда:
        tail = name[len(canon):]
        if keys[canon].get("glued"):
            # Хвост — легитимное слитное значение (/Lru = /L + «ru»).
            # Молча пропускать нельзя: так же устроены и выдуманные
            # /Publish, /NewConfiguration, /OptimizeDatabase,
            # /WSAuthentication — тоже начинаются с glued-ключа. Блокировать
            # нельзя: /Lru и /Padmin работают (проверено запуском: /Lru +
            # /DumpCfg создал файл). Остаётся назвать сомнение вслух, с
            # нулевым кодом возврата.
            used.append((canon, i))
            notes.append(
                "%s — точно такого ключа в документации 8.3.27 нет; разобран "
                "как %s со значением «%s». Если имелся в виду другой ключ, "
                "он выдуман" % (a, canon, tail))
        else:
            # Хвост — не значение, а позиционный аргумент, который платформа
            # отправляет отдельно от ключа (только для ключей, чей arg —
            # «голое» значение, см. absorbs_glued_tail). Это уже проверено
            # запуском трижды и всякий раз неверно: /DumpCfgToFile и
            # /OutBase выполняют операцию, но не в тот файл (тихая порча),
            # /LoadCfgFromFile падает кодом 1 «Файл не обнаружен»
            # (docs/evidence/2026-08-22-blocking-rules.md). В отличие от
            # glued-случая (/Proxy, /NoProxy живут отдельно и не участвуют
            # в этой ветке вовсе — их arg не «голый»), здесь платформа
            # доказанно не делает того, что написано в команде — правило 11
            # требует блокировки, а не предупреждения.
            problems.append(
                "%s — такого ключа нет в документации 8.3.27; платформа "
                "разберёт совпадение как %s с хвостом «%s», отправленным "
                "не в значение ключа, а в позиционный аргумент — операция "
                "уйдёт не туда или не выполнится вовсе (проверено запуском "
                "на /DumpCfgToFile, /OutBase и /LoadCfgFromFile)" % (a, canon, tail))

    if used and any(n == "/@" for n, _ in used) and used[0][0] != "/@":
        # Раздел 7.3.11: «Команда /@ должна быть первой или единственной
        # командой командной строки запуска приложения. Если команда /@
        # указана не первой ‑ поведение является неопределенным.» «Неопределено»
        # — не «запрещено»: платформа не гарантированно откажет, поэтому
        # это предупреждение, а не блокировка (правило 11: блокировать
        # можно только доказанно неверное, а это не проверено запуском).
        notes.append(
            "/@ указан не первым ключом — раздел 7.3.11 руководства "
            "администратора называет поведение в этом случае неопределённым "
            "(содержимое файла должно было заменить собой всю командную "
            "строку целиком)")

    for name, _ in used:
        # modes — список: ключ, документированный в нескольких разделах
        # (например /DumpResult — в 7.2.3 и 7.4.17), несёт оба. Пустой
        # список — «общий»: ключ не ограничен по режиму вовсе.
        restricted = [m for m in (keys[name].get("modes") or []) if m in MODE_WORDS]
        if not (mode and restricted and mode not in restricted):
            continue
        where = "%s работает в режиме %s, а команда запущена как %s" % (
            name, "/".join(restricted), mode)
        if "DESIGNER" in restricted:
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
    argv = sys.argv[1:]
    if argv and argv[0] in ("-h", "--help"):
        # М-25: без этого argv[0] == "--help" уходил дальше как обычная
        # команда для проверки — tool.startswith("1cv8") давал False, и
        # скрипт молча отвечал «--help вне компетенции проверяльщика»
        # вместо помощи.
        print(__doc__.strip())
        return 0
    line = " ".join(argv).strip()
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
