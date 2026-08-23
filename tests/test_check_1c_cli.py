"""Регрессия проверяльщика командной строки.

Каждый тест соответствует дефекту из docs/plan.md, подтверждённому запуском.
Запуск: python -m pytest tests/test_check_1c_cli.py -v
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "1c-build-and-db" / "scripts" / "check-1c-cli.py"

spec = importlib.util.spec_from_file_location("check_1c_cli", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["check_1c_cli"] = mod
spec.loader.exec_module(mod)

CATALOG = mod.load_catalog()


def problems(line):
    return mod.check(line, CATALOG)[0]


def notes(line):
    return mod.check(line, CATALOG)[1]


def exit_code(line):
    """Код возврата настоящего запуска: навык обещает «0 — можно запускать»."""
    return subprocess.run([sys.executable, str(SCRIPT), line]).returncode


def test_d13_invented_key_is_rejected():
    """Д-13: /DumpCfgToFile не существует и не должен проходить за /DumpCfg."""
    out = problems("1cv8 DESIGNER /F d:/base /DumpCfgToFile d:/x.cf "
                   "/DisableStartupDialogs /Out d:/l.log")
    assert any("DumpCfgToFile" in p for p in out), out


def test_d13_glued_value_key_still_works():
    """Слитные ключи со значением остаются законными: /L<код языка>.

    Законными — значит не блокируются. Предупреждение при этом выдаётся, см.
    test_glued_prefix_costs_a_note_on_legit_keys: отличить /Lru от выдуманного
    /LoadCfgFromFile механически нельзя, и цена честности платится здесь.
    """
    assert problems("1cv8 DESIGNER /F d:/base /Lru /DumpCfg d:/x.cf "
                    "/DisableStartupDialogs /Out d:/l.log") == []


# Четыре выдуманных ключа, каждый из которых начинается со слитного: /P, /N,
# /O, /WSA. До правки все проходили молча с кодом 0 — то есть главное
# обещание проверяльщика («ловит выдуманный ключ») держалось только для ключей,
# не начинающихся со слитного.
#
# /LoadCfgFromFile раньше был в этом списке пятым, потому что старый known_key
# искал совпадение только среди двенадцати glued-ключей и ложно резолвил его
# в /L. Н-02: платформа берёт самое длинное совпадение среди ВСЕХ ключей —
# для /LoadCfgFromFile это /LoadCfg, не glued, и хвост «FromFile» уходит не в
# значение, а в позиционный аргумент. Это уже проверено запуском (платформа
# отвечает кодом 1, «Файл не обнаружен»), поэтому теперь у него другая пара —
# см. INVENTED_LONGEST_MATCH_BLOCKS и test_longest_match_off_glued_prefix_blocks.
INVENTED_ON_GLUED = [
    ("/Publish", "/P"),
    ("/NewConfiguration", "/N"),
    ("/OptimizeDatabase", "/O"),
    ("/WSAuthentication", "/WSA"),
]


def line_with(key):
    return ("1cv8 DESIGNER /F d:/base %s d:/x.cf /DisableStartupDialogs "
            "/Out d:/l.log" % key)


@pytest.mark.parametrize("key,canon", INVENTED_ON_GLUED)
def test_glued_prefix_invented_key_warns_and_does_not_block(key, canon):
    """Выдуманный ключ на слитном префиксе называется вслух, но не блокируется.

    Блокировать нельзя: /Publish и /Padmin, /LoadCfgFromFile и /Lru устроены
    одинаково — слитный ключ плюс буквы. Проверено запуском, что законная
    половина работает (/Lru + /DumpCfg создал файл), а значит запрет остановил
    бы верное. Правило 11 архитектуры: не показал — не блокируй.
    """
    assert problems(line_with(key)) == [], problems(line_with(key))
    out = notes(line_with(key))
    assert any(key in n and canon in n for n in out), out
    assert exit_code(line_with(key)) == 0


@pytest.mark.parametrize("key", ["/Lru", "/Padmin"])
def test_glued_prefix_costs_a_note_on_legit_keys(key):
    """Цена решения: законный слитный ключ тоже получает предупреждение.

    Это осознанно. Эвристика «хвост похож на имя ключа» не спасает: у /Publish
    хвост «ublish», у /Padmin — «admin», оба строчные и одной длины.
    """
    assert problems(line_with(key)) == [], problems(line_with(key))
    assert any(key in n for n in notes(line_with(key))), notes(line_with(key))
    assert exit_code(line_with(key)) == 0


def test_invented_key_off_glued_prefix_still_blocks():
    """Защита точным совпадением на месте: /DumpCfgToFile — ошибка и код 1."""
    line = line_with("/DumpCfgToFile")
    assert any("DumpCfgToFile" in p for p in problems(line)), problems(line)
    assert exit_code(line) == 1


def test_known_key_matches_platform_longest_match():
    """Н-02, повторное ревью: «самое длинное совпадение среди ВСЕХ ключей» —
    неверная формула буквально (см. test_longest_prefix_is_not_the_whole_rule
    ниже, /PRoxy2024). Верно то, что она случайно предсказала правильно
    здесь: /LoadCfg и /DumpCfg участвуют в совпадении, потому что их arg —
    «голое» позиционное значение (absorbs_glued_tail), а /LoadCfg и /DumpCfg
    оказываются длиннее /L — единственного короткого конкурента, у которого
    в этих двух случаях реального длинного «под-ключевого» соперника нет.

    Проверено запуском: /LoadCfgFromFile платформа разбирает как /LoadCfg
    с позиционным аргументом FromFile, а не как /L со значением.
    """
    keys = CATALOG["ключи"]
    assert mod.known_key("/LoadCfgFromFile", keys) == "/LoadCfg"
    assert mod.known_key("/DumpCfgToFile", keys) == "/DumpCfg"
    assert mod.known_key("/Lru", keys) == "/L"


def test_longest_prefix_is_not_the_whole_rule():
    """Н-02, находка ревью «новая блокировка законного» (Critical): формула
    «самое длинное совпадение среди ВСЕХ ключей» блокировала бы законный
    /PRoxy2024 — резолвился бы в /Proxy (длиннее /P), хотя платформа его
    туда не резолвит вовсе.

    Проверено запуском (2026-08-23): `/N Admin /PRoxy2024` и контрольный
    `/N Admin /Padmin123` дают ОДИНАКОВУЮ ошибку «Пользователь ИБ не
    идентифицирован» — платформа взяла /P + «Roxy2024» как пароль, а не
    /Proxy. /Proxy при этом не сломан: с настоящими -PSrv/-PPort он прошёл
    штатно, код 0 (см. docs/evidence/2026-08-22-blocking-rules.md).

    Настоящий критерий — absorbs_glued_tail: /Proxy требует именованный
    под-ключ первым делом (`-PSrv <адрес> ...`), глued-хвост эту форму не
    удовлетворяет, поэтому /Proxy не участвует в совпадении вовсе, и
    остаётся единственный кандидат — /P.
    """
    keys = CATALOG["ключи"]
    assert mod.known_key("/PRoxy2024", keys) == "/P"
    assert "/Proxy" in keys and not keys["/Proxy"].get("glued")


def test_empty_arg_key_does_not_absorb_a_tail():
    """Тот же критерий, другая форма отказа: /NoProxy вовсе не берёт
    аргумента (`arg` пуст в cli-keys.json) — глued-хвосту нечем удовлетворить
    пустую форму, и /NoProxy тоже не участвует в совпадении.

    Проверено запуском (2026-08-23): `/NoProxyUser` даёт ту же ошибку
    «Пользователь ИБ не идентифицирован», что и /N Admin — платформа взяла
    /N + «oProxyUser» как имя пользователя, а не /NoProxy.
    """
    keys = CATALOG["ключи"]
    assert mod.known_key("/NoProxyUser", keys) == "/N"
    assert "/NoProxy" in keys and keys["/NoProxy"].get("arg") == ""


# Резолвятся в ключ, чей arg — «голое» позиционное значение (absorbs_glued_tail
# без учёта glued): хвост уходит не в значение, а в позиционный аргумент,
# который платформа отправляет сама. Проверено запуском трижды и всякий раз
# неверно: /DumpCfgToFile и /OutBase выгружают/логируют не в тот файл — тихая
# порча (docs/evidence/2026-08-22-blocking-rules.md), /LoadCfgFromFile падает
# кодом 1, «Файл не обнаружен». Во всех трёх платформа доказанно не делает
# того, что написано в команде — правило 11 требует блокировки.
INVENTED_LONGEST_MATCH_BLOCKS = [
    ("/LoadCfgFromFile", "/LoadCfg"),
    ("/DumpCfgToFile", "/DumpCfg"),
    ("/OutBase", "/Out"),
]


@pytest.mark.parametrize("key,canon", INVENTED_LONGEST_MATCH_BLOCKS)
def test_longest_match_off_glued_prefix_blocks(key, canon):
    """Н-02: хвост-позиционный-аргумент — это не то же самое, что
    хвост-значение (test_glued_prefix_invented_key_warns_and_does_not_block),
    и различить их теперь можно: по форме arg резолвнутого ключа
    (absorbs_glued_tail), а не по одному лишь факту «длиннее».
    """
    line = line_with(key)
    out = problems(line)
    assert any(key in p and canon in p for p in out), out
    assert exit_code(line) == 1


# Наивная «самая длинная строка длиннее» правильно предсказывала бы /Proxy и
# /NoProxy как победителей — платформа выбирает короткий glued-ключ, потому
# что длинный кандидат не может принять хвост как своё значение (см.
# test_longest_prefix_is_not_the_whole_rule и test_empty_arg_key_does_not_absorb_a_tail
# выше). Здесь — регресс на уровне check(): такие команды не блокируются.
NOT_LONGEST_MATCH_STAYS_GLUED = [
    ("/PRoxy2024", "/P"),
    ("/NoProxyUser", "/N"),
]


@pytest.mark.parametrize("key,canon", NOT_LONGEST_MATCH_STAYS_GLUED)
def test_named_subflag_key_does_not_steal_the_match(key, canon):
    """Критическая находка повторного ревью: /Proxy (`-PSrv ...`) и /NoProxy
    (пустой arg) длиннее /P и /N соответственно, но не могут принять хвост
    как своё значение — платформа проверено откатывается к короткому
    glued-ключу, и блокировать эти команды было бы новой блокировкой
    законного.
    """
    line = line_with(key)
    assert problems(line) == [], problems(line)
    out = notes(line)
    assert any(key in n and canon in n for n in out), out
    assert exit_code(line) == 0


def test_proxy_with_required_subflags_is_an_exact_match():
    """/Proxy написан правильно (с обязательными -PSrv/-PPort) — это точное
    совпадение по имени ключа, а не хвост-коллизия с /P. Проверено запуском:
    команда с настоящими -PSrv/-PPort отработала, код 0, файл создан
    (docs/evidence/2026-08-22-blocking-rules.md).
    """
    assert mod.known_key("/Proxy", CATALOG["ключи"]) == "/Proxy"
    line = ("1cv8 DESIGNER /F d:/base /Proxy -PSrv 127.0.0.1 -PPort 8080 "
            "/DumpCfg d:/x.cf /DisableStartupDialogs /Out d:/l.log")
    assert problems(line) == [], problems(line)


# Третий раунд ревью, Critical: absorbs_glued_tail() признаёт кандидатом на
# поглощение около пятидесяти НЕ-glued ключей (/S, /WS, /C,
# /ConfigurationRepositoryF и другие — все с «голым» arg), но блокировка по
# одному лишь признаку «не glued» была обобщением без своего прогона.
# Рецензент собрал шесть таких команд и прогнал одну: DESIGNER
# /Snosuchhost9999:1541/nodb — платформа разобрала /S<адрес> ВЕРНО
# (server_addr=nosuchhost9999, «Этот хост неизвестен» — ошибка DNS, не
# разбора). Переподтверждено координатором тем же прогоном.
def test_proven_and_only_proven_keys_block_the_tail():
    """Блокировка (не предупреждение) — только у трёх ключей из
    PROVEN_TAIL_MISPARSE, каждый подтверждён своим прогоном. /S не входит в
    этот список и не должен блокироваться, несмотря на то что участвует в
    absorbs_glued_tail так же, как /LoadCfg/DumpCfg/Out.
    """
    assert mod.PROVEN_TAIL_MISPARSE.keys() == {"/LoadCfg", "/DumpCfg", "/Out"}
    assert "/S" not in mod.PROVEN_TAIL_MISPARSE


def test_glued_address_key_is_not_blocked():
    """Критическая находка третьего раунда ревью: /S<адрес> (клиент-
    серверная база, раздел 7.3.1) не glued, но участвует в
    absorbs_glued_tail — платформа проверено разбирает его верно, значит
    блокировать нельзя.

    Проверено запуском (2026-08-23): `DESIGNER /Snosuchhost9999:1541/nodb`
    дал `server_addr=nosuchhost9999`, «Этот хост неизвестен» — ошибка DNS
    несуществующего хоста, а не разбора ключа. Платформа взяла /S с
    хвостом «nosuchhost9999:1541/nodb» как значение, ровно как задокумен-
    тировано (раздел 7.3.1: `/S<адрес сервера>[:<порт>][/<имя базы>]`).
    """
    line = ("1cv8 DESIGNER /Snosuchhost9999:1541/nodb "
            "/DisableStartupDialogs /Out d:/l.log")
    assert mod.known_key("/Snosuchhost9999:1541/nodb", CATALOG["ключи"]) == "/S"
    assert problems(line) == [], problems(line)
    out = notes(line)
    assert any("/S" in n and "не проверял" in n for n in out), out
    assert exit_code(line) == 0
    # /S всё равно засчитан как заданная база — не должно быть побочной
    # «не задана база» из-за того, что резолвнутый ключ не попал в used.
    assert not any("не задана база" in p for p in problems(line))


@pytest.mark.parametrize("key,canon", [
    ("/WShttp://example.com/base", "/WS"),
    ("/Cmytext", "/C"),
    ("/ConfigurationRepositoryFd:/storage", "/ConfigurationRepositoryF"),
    ("/ConvertFilesd:/some.cf", "/ConvertFiles"),
    ("/DumpDBCfgd:/db.cf", "/DumpDBCfg"),
])
def test_unproven_absorbing_family_warns_not_blocks(key, canon):
    """Пять дальнейших ключей того же семейства (та же природа коллизии,
    что у /S) — тоже не в PROVEN_TAIL_MISPARSE, тоже должны предупреждать,
    а не блокировать. Живым запуском не проверялись поштучно (кроме /S) —
    и текст предупреждения обязан честно говорить «не проверялось», а не
    претендовать на проверку, которой не было.
    """
    line = "1cv8 DESIGNER /F d:/base %s /DisableStartupDialogs /Out d:/l.log" % key
    assert mod.known_key(key, CATALOG["ключи"]) == canon
    assert problems(line) == [], problems(line)
    out = notes(line)
    assert any(canon in n and "не проверял" in n for n in out), out
    assert exit_code(line) == 0


def test_glued_flag_is_present_and_small():
    """Признак glued проставлен и стоит ровно у 12 ключей."""
    glued = [k for k, v in CATALOG["ключи"].items() if v.get("glued")]
    assert len(glued) == 12, glued
    assert "/L" in glued and "/DumpCfg" not in glued, glued


def test_glued_prefix_collision_picks_longest_match():
    """/O и /OIDA оба glued; /OIDAOff обязан разрешиться в /OIDA, а не в /O.

    known_key перебирает keys.items() и обязан брать самое длинное совпадение,
    а не первое попавшееся — иначе более короткий glued-ключ ложно перехватывает
    значение более длинного.
    """
    assert mod.known_key("/OIDAOff", CATALOG["ключи"]) == "/OIDA"


def test_d14_env_var_is_allowed():
    """Д-14: %TEMP% — законный переносимый путь."""
    assert problems("1cv8 DESIGNER /F d:/base /LoadCfg d:/n.cf "
                    "/DisableStartupDialogs /Out %TEMP%/load.log "
                    "/DumpResult %TEMP%/rc.txt") == []


def test_d15_real_name_with_vash_is_allowed():
    """Д-15: «Ваш Дом» — настоящее название организации."""
    assert problems('1cv8 DESIGNER /F "d:/Базы/ООО Ваш Дом" /LoadCfg d:/n.cf '
                    "/DisableStartupDialogs /Out d:/l.log /DumpResult d:/rc.txt") == []


def test_d16_lowercase_key_is_allowed():
    """Д-16: ключи 1С регистронезависимы, проверено запуском."""
    assert problems("1cv8 DESIGNER /F d:/base /loadcfg d:/n.cf "
                    "/DisableStartupDialogs /Out d:/l.log /DumpResult d:/rc.txt") == []


FOREIGN = "ibcmd infobase config load --db-path=d:/base --file=d:/new.cf"


def test_d17_foreign_tool_is_not_judged():
    """Д-17: ibcmd не 1cv8; скрипт не судит чужой инструмент и не запрещает его.

    Прежняя редакция теста требовала ровно одну запись в problems — то есть
    закрепляла код возврата 1 на инструменте, который рекомендует наш же
    рецепт (references/load-configuration.md, шаг 3). Граница компетенции —
    это замечание, а не приговор.
    """
    assert problems(FOREIGN) == [], problems(FOREIGN)
    out = notes(FOREIGN)
    assert len(out) == 1, out
    assert "вне компетенции" in out[0], out


def test_d17_foreign_tool_returns_zero():
    """SKILL.md обещает «код возврата 0 — можно запускать». Проверяем запуском."""
    assert exit_code(FOREIGN) == 0


def test_c1_ib_connection_string_sets_the_base():
    """/IBConnectionString задаёт базу наравне с /F.

    М-16: докстрока и проверка раньше расходились — докстрока ссылалась на
    запуск DESIGNER + /DumpCfg, а сама проверка гоняла ENTERPRISE без
    /DumpCfg вовсе, то есть заявляла одно, а проверяла другое.

    Проверено запуском на 8.3.27.2325: DESIGNER /IBConnectionString
    "File=D:/1C/base/trade;" /DumpCfg создал файл того же размера, что и
    выгрузка через /F (docs/evidence/2026-08-22-blocking-rules.md, случай
    «строка-соединения»). Теперь проверка гоняет ровно этот запуск.
    """
    assert problems('1cv8 DESIGNER /IBConnectionString "File=d:/base;" '
                    "/DumpCfg d:/x.cf /DisableStartupDialogs /Out d:/l.log") == []


def test_c1_lowercase_base_key_is_allowed():
    """Регистр не важен и для ключа базы: /f — та же база, что /F."""
    assert problems("1cv8 DESIGNER /f d:/base /dumpcfg d:/out.cf "
                    "/disablestartupdialogs") == []


def test_no_base_still_blocks():
    """Незаданная база остаётся ошибкой: платформа отвечает «Неопределена
    информационная база», код 1, файла нет — проверено запуском."""
    out = problems("1cv8 DESIGNER /DumpCfg d:/x.cf /DisableStartupDialogs /Out d:/l.log")
    assert any("не задана база" in p for p in out), out


def test_no_mode_still_blocks():
    """Неуказанный режим остаётся ошибкой: «Неопределен режим запуска», код 1."""
    out = problems("1cv8 /F d:/base /DumpCfg d:/x.cf /DisableStartupDialogs /Out d:/l.log")
    assert any("режим запуска" in p for p in out), out


def test_config_word_is_not_a_recognized_mode():
    """М-14: CONFIG был в MODE_WORDS, хотя не документирован ни как режим
    запуска 8.3.27, ни в тексте ошибки, ни у единого ключа каталога.

    Раздел 7.3.3 руководства администратора называет CONFIG, но только как
    замену, которую платформа выполняет САМА при автоподборе версии для
    запуска настоящего 1С:Предприятия 8.0 (/AppAutoCheckVersion) — это
    внутренний механизм для другого исполняемого файла, а не режим запуска,
    который стоит писать в команде для 8.3.27. Раньше CONFIG в MODE_WORDS
    молча гасил «не указан режим запуска» там, где такого режима у 8.3.27
    нет вовсе.
    """
    out = problems("1cv8 CONFIG /F d:/base /DumpCfg d:/x.cf "
                   "/DisableStartupDialogs /Out d:/l.log")
    assert any("режим запуска" in p for p in out), out


def test_alien_mode_key_inside_designer_is_only_a_note():
    """Ключ чужого режима внутри пакетного DESIGNER не блокируется.

    Проверено запуском: DESIGNER /F <база> /UsePrivilegedMode /DumpCfg
    отработал, файл создан и совпал по размеру с обычной выгрузкой. Правило 11
    архитектуры: не показал — не блокируй.
    """
    line = ("1cv8 DESIGNER /F d:/base /UsePrivilegedMode /DumpCfg d:/x.cf "
            "/DisableStartupDialogs /Out d:/l.log")
    assert problems(line) == [], problems(line)
    assert any("UsePrivilegedMode" in n for n in notes(line)), notes(line)


def test_alien_option_is_only_a_note():
    """Опция не от этого ключа не блокируется: платформа её приняла.

    Проверено запуском: DESIGNER /F <база> /DumpCfg <файл> -Format Hierarchical
    отработал, файл создан и побайтно того же размера, что и без опции.
    """
    line = ("1cv8 DESIGNER /F d:/base /DumpCfg d:/x.cf -Format Hierarchical "
            "/DisableStartupDialogs /Out d:/l.log")
    assert problems(line) == [], problems(line)
    assert any("-Format" in n for n in notes(line)), notes(line)


def test_placeholder_still_blocks():
    """Заглушка версии остаётся ошибкой: путь не существует."""
    assert any("8.3.xx" in p for p in problems(
        r'"C:\Program Files\1cv8\8.3.xx.yyyy\bin\1cv8.exe" DESIGNER /F d:/base '
        "/LoadCfg d:/n.cf /DisableStartupDialogs /Out d:/l.log"))


def test_wrong_mode_still_blocks():
    """Пакетный ключ конфигуратора вне DESIGNER остаётся ошибкой.

    Проверено запуском: ENTERPRISE /F <база> /LoadCfg <файл>
    /DisableStartupDialogs не загрузил ничего — платформа открыла сеанс и не
    вернула управление, процесс убит по таймауту 60 секунд, журнал пуст,
    /DumpResult не создан.
    """
    assert any("режиме" in p for p in problems(
        "1cv8 ENTERPRISE /F d:/base /LoadCfg d:/n.cf /Out d:/l.log"))


def test_catalog_completeness_against_source():
    """Н-03, Н-08: состав каталога сверяется с приложением 7 программно.

    Источник — _its/cmdline/its-pril7-full.json. Если выгрузки нет на машине,
    тест пропускается: каталог _its/ под gitignore и у пользователя его нет.
    """
    import pytest
    src = ROOT / "_its" / "cmdline" / "its-pril7-full.json"
    if not src.exists():
        pytest.skip("выгрузка ИТС недоступна: каталог _its/ под gitignore")
    keys = CATALOG["ключи"]
    assert "/@" in keys, "документированный ключ /@ (раздел 7.3.11) отсутствует"
    assert isinstance(keys["/DumpResult"]["modes"], list), "режим обязан быть списком"
    assert len(keys["/DumpResult"]["modes"]) >= 2, (
        "/DumpResult описан в двух режимах: 7.2.3 и 7.4.17")


AT_KEY_NOT_FIRST = ("1cv8 DESIGNER /F d:/base /DumpCfg d:/x.cf /@ d:/cmd.txt "
                    "/DisableStartupDialogs /Out d:/l.log")


def test_at_key_not_first_only_warns():
    """Н-08 (найдено повторным ревью): /@ добавили в каталог, но не хватало
    правила позиции — команда с /@ не первым ключом проходила без единого
    замечания, хотя документация называет это неопределённым поведением.

    Раздел 7.3.11 руководства администратора, дословно: «Команда /@ должна
    быть первой или единственной командой командной строки запуска
    приложения. Если команда /@ указана не первой ‑ поведение является
    неопределенным.» «Неопределено» — не «запрещено»: платформой это не
    проверено запуском, поэтому правило 11 архитектуры («блокировать только
    доказанно неверное») требует предупреждения, а не ошибки.
    """
    assert problems(AT_KEY_NOT_FIRST) == [], problems(AT_KEY_NOT_FIRST)
    out = notes(AT_KEY_NOT_FIRST)
    assert any("/@" in n and "не первым" in n for n in out), out
    assert exit_code(AT_KEY_NOT_FIRST) == 0


@pytest.mark.parametrize("line", [
    # /@ — первый /-ключ команды (перед ним только слово режима, не ключ).
    "1cv8 DESIGNER /@ d:/cmd.txt /F d:/base /DisableStartupDialogs",
    # /@ — единственный ключ команды вообще (условие «или единственной»).
    "1cv8 /@ d:/cmd.txt",
    # I-6: тот самый случай из документации, который блокировался. Режима и
    # базы в строке нет — и не должно быть: содержимое файла заменит собой
    # командную строку целиком.
    "1cv8 /@d:/cmd.txt",
    "1cv8 DESIGNER /@ d:/cmd.txt",
])
def test_at_key_first_is_clean(line):
    """Законные команды с /@ первым (или единственным) ключом.

    I-6: раньше докстрока обещала «правило не должно заводить новую
    блокировку», а проверялось только отсутствие замечания «не первым» —
    заявление шире доказательства. При этом «1cv8 /@ d:/cmd.txt» как раз
    блокировалась двумя ошибками: K002 «не указан режим» и K007 «не задана
    база», код 1.

    Раздел 7.3.11 дословно: «Во время обработки командной строки, содержимое
    файла полностью заменит собой командную строку запускаемого приложения»,
    и отсюда «команда /@ должна быть первой или единственной». Режим, база и
    /DisableStartupDialogs лежат в файле — требовать их в самой строке значит
    блокировать документированную команду. Global Constraints плана называют
    новую блокировку законного Critical.
    """
    assert problems(line) == [], problems(line)
    assert exit_code(line) == 0, problems(line)
    assert not any("/@" in n and "не первым" in n for n in notes(line)), notes(line)
    assert not any(n.startswith("K014") or "K014" in n for n in notes(line)), notes(line)


@pytest.mark.parametrize("line", [
    # Без /@ требование режима и базы остаётся: I-6 сужает правило до /@,
    # а не отменяет его.
    "1cv8 DESIGNER /DumpCfg d:/a.cf",
    "1cv8 /DumpCfg d:/a.cf",
])
def test_missing_base_still_blocks_without_at_key(line):
    """I-6 не имеет права ослабить проверку там, где /@ нет."""
    out = problems(line)
    assert any("K007" in p for p in out), out
    assert exit_code(line) == 1


# Самое дорогое ограничение проекта: «скрипт блокирует только противоречащее
# документированному составу приложения 7; новая блокировка законного —
# Critical». За ветку блокировка законного вносилась дважды, и оба раза её
# ловило только ревью — то есть человек, а не прогон. Здесь она ловится
# прогоном: каждая команда 1cv8, которую навык показывает читателю как рабочую,
# обязана проходить собственный проверяльщик с кодом 0.
_CMD_RE = re.compile(r"(?:^|[\s\"'`(])(1cv8(?:\.exe)?\s+[^\r\n`]*)")


def _commands_from_skill_bodies():
    """Команды 1cv8 из SKILL.md, references/ и scripts/ обоих навыков."""
    targets = (sorted(ROOT.glob("skills/*/SKILL.md"))
               + sorted(ROOT.glob("skills/*/references/*.md"))
               + sorted(ROOT.glob("skills/*/scripts/*.py")))
    found = []
    for f in targets:
        rel = f.relative_to(ROOT).as_posix()
        for lineno, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for m in _CMD_RE.finditer(line):
                cmd = m.group(1).strip().rstrip("\\`\"'").strip()
                if cmd:
                    found.append(pytest.param(cmd, id="%s:%d" % (rel, lineno)))
    return found


_SKILL_COMMANDS = _commands_from_skill_bodies()


def test_skill_bodies_actually_contain_commands():
    """Сторож самого сторожа: пустой список молча прошёл бы за успех."""
    assert len(_SKILL_COMMANDS) >= 8, _SKILL_COMMANDS


@pytest.mark.parametrize("line", _SKILL_COMMANDS)
def test_no_command_from_skill_bodies_is_blocked(line):
    """Ни одна показанная навыком команда не блокируется проверяльщиком."""
    out = problems(line)
    assert out == [], "команда из тела навыка заблокирована: %s -> %s" % (line, out)


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_flag_prints_docstring_and_returns_zero(flag):
    """М-25: скрипт не отвечал на --help вовсе — argv[0] == "--help" уходил
    как обычная команда на проверку, tool.startswith("1cv8") давал False, и
    вместо помощи печаталось «--help вне компетенции проверяльщика».
    """
    out = subprocess.run([sys.executable, str(SCRIPT), flag],
                         capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    assert out.returncode == 0, out
    assert "вне компетенции" not in out.stdout, out.stdout
    assert "Проверка командной строки" in out.stdout, out.stdout


# Н-14: диагностики получили идентификатор — на них можно сослаться и их
# можно процитировать в тесте, не цепляясь за обрывок прозы, которую правка
# текста меняет незаметно для теста (docs/reviews/2026-08-23-core-review.md).
CODE_PATTERN = re.compile(r"^K\d{3}$")


def test_diagnostic_codes_are_unique_and_well_formed():
    """Каждая константа K_* — трёхзначный код без пропусков и дублей."""
    codes = [v for k, v in vars(mod).items()
             if k.startswith("K_") and isinstance(v, str)]
    assert len(codes) >= 10, codes  # ~10 диагностик, как называет находка
    assert all(CODE_PATTERN.match(c) for c in codes), codes
    assert len(codes) == len(set(codes)), "коды не должны повторяться: %s" % codes


def test_format_diag_splits_code_from_text():
    """format_diag() кладёт код в скобки рядом с уровнем, а не в текст:
    «[ошибка K999] текст», по образцу линтеров — ровно то, что просит находка.
    """
    assert mod.format_diag("ошибка", "K999 текст без кода") == "[ошибка K999] текст без кода"
    # Строка без кода (гипотетическая) не ломается — код просто не появляется.
    assert mod.format_diag("внимание", "текст совсем без кода") == "[внимание] текст совсем без кода"


def test_no_base_error_is_addressable_by_code():
    """Живой прогон печатает код диагностики, а не только прозу — K007 можно
    процитировать в доказательстве или отключить точечно в будущем, не трогая
    формулировку. Проверено запуском самого скрипта, не только check()."""
    out = subprocess.run(
        [sys.executable, str(SCRIPT),
         "1cv8 DESIGNER /DumpCfg d:/x.cf /DisableStartupDialogs /Out d:/l.log"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert out.returncode == 1, out
    assert "[ошибка K007]" in out.stdout, out.stdout


def test_proven_misparse_error_is_addressable_by_code():
    """K004 — тот же принцип для блокировки PROVEN_TAIL_MISPARSE."""
    out = subprocess.run(
        [sys.executable, str(SCRIPT), line_with("/DumpCfgToFile")],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert out.returncode == 1, out
    assert "[ошибка K004]" in out.stdout, out.stdout


def test_foreign_tool_note_is_addressable_by_code():
    """K017 — то же для границы компетенции (Д-17)."""
    out = subprocess.run(
        [sys.executable, str(SCRIPT), FOREIGN],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert out.returncode == 0, out
    assert "[внимание K017]" in out.stdout, out.stdout
