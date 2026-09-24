# Блокировки и изоляция на уровне СУБД: где правило 1С опирается на чужое поведение

**Ищут по словам:** уровень изоляции, Read Committed, RCSI,
`READ_COMMITTED_SNAPSHOT`, snapshot, MVCC, эскалация блокировок, 5000 блокировок,
`LOCK_ESCALATION`, `LOCK_TIMEOUT`, `lock_timeout`, `deadlock_timeout`,
взаимоблокировка, жертва взаимоблокировки, ошибка 1205, ошибка 1222,
«грязное» чтение, `READ UNCOMMITTED`, `NOLOCK`, повторное чтение в транзакции,
PostgreSQL против MS SQL, почему запрос видит разные данные.

**Источники.** Руководство разработчика 8.3.27, §9.2.3.1–9.2.3.6 (разбор —
в `data-mechanics.md`); стандарты 460, 648, 659, 661, 783 (разбор —
в `transactions-and-locks.md`); документация PostgreSQL 17 и Microsoft Learn
по SQL Server (view=sql-server-ver16). Английские цитаты приводятся дословно,
пересказ по-русски рядом помечен как пересказ.

**Поведение СУБД здесь описано по документации и запуском не проверено**
(решение 24: живой СУБД у набора нет). И вторая оговорка, без которой
первая неполна: в ИТС фигурируют сборки **PostgreSQL 16.x и 17.x «…1C»** —
сборки с патчами 1С, и документация PostgreSQL их отличий не описывает.
Где ИТС говорит о сборке, ИТС главнее.

**Спина разбора: стандарты 1С дают правило, но не причину, а причина живёт
в чужой системе.** «Блокируйте перед чтением», «не держите транзакцию
дольше 20 секунд» — верные правила; из них не видно, что за ними стоят два
разных менеджера блокировок с разными числами, разными умолчаниями и разным
поведением при отказе.

## Управляемые блокировки — это блокировки 1С, а не СУБД

Руководство называет порог эскалации: «если на одно пространство
накладывается более 100 000 блокировок, то может произойти эскалация
блокировки» (§9.2.3.6). Это **платформенное** число, и с числами СУБД
у него общего нет:

- **MS SQL.** «Lock escalation is triggered when … A single Transact-SQL
  statement acquires at least 5,000 locks on a single nonpartitioned table
  or index» — пересказ: порог у SQL Server в двадцать раз ниже и считается
  не на пространство блокировки 1С, а на один оператор и одну таблицу;
- **PostgreSQL.** Эскалации строковых блокировок нет вовсе: «PostgreSQL
  doesn't remember any information about modified rows in memory, so there
  is no limit on the number of rows locked at one time» — пересказ: число
  заблокированных строк ничем не ограничено, потому что блокировка живёт
  в самой строке на диске. Ограничен другой счёт — объектов:
  «max_locks_per_transaction … This is not the number of rows that can be
  locked; that value is unlimited. The default, 64».

**Вывод набора, а не источника.** Из этого следуют две вещи, которых
в стандартах нет. Первая: отключить эскалацию средствами СУБД
(`ALTER TABLE SET LOCK_ESCALATION`) — не значит отключить эскалацию 1С;
это разные механизмы с разными порогами. Вторая: совет блокировать
по значениям измерений, а не пространство целиком (std460), на PostgreSQL
экономит не память менеджера блокировок, а конкуренцию, — предела
на число строк там нет.

## Read Committed у двух СУБД — два разных обещания

Руководство приводит уровни изоляции по СУБД (§9.2.3.2): в управляемом
режиме — Read Committed, а у MS SQL Server 2005 и выше — «Read Committed
Snapshot». Что это значит, руководство не объясняет.

**MS SQL: RCSI — это версии строк, а не блокировки.** «When the
READ_COMMITTED_SNAPSHOT database option is set ON … the READ COMMITTED
isolation level uses row versioning to provide statement-level read
consistency. Read operations require only the schema stability (Sch-S)
table level locks and no page or row locks» — пересказ: читающие
не ставят блокировок строк и страниц и не ждут пишущих; каждый **оператор**
видит согласованный снимок.

**PostgreSQL: то же обещание, но всегда.** «Read Committed is the default
isolation level in PostgreSQL. When a transaction uses this isolation
level, a SELECT query (without a FOR UPDATE/SHARE clause) sees only data
committed before the query began» — снимок на **начало запроса**,
без всякой настройки базы.

**И общая цена, названная обеими сторонами.** PostgreSQL: «two successive
SELECT commands can see different data, even though they are within
a single transaction, if other transactions commit changes after the first
SELECT starts and before the second SELECT starts». Руководство 1С говорит
то же короче: в управляемом режиме «не обеспечивается воспроизводимость
чтения данных в транзакции» (§9.2.3.2).

**Отсюда механика правила std648** — блокировать перед чтением, если
считанное будет изменено или должно остаться неизменным. Это не общий
совет осторожности, а единственный способ получить повторяемость чтения
там, где СУБД её не даёт: снимок берётся на каждый оператор, и второй
`SELECT` в той же транзакции законно вернёт другое.

## Двадцать секунд — платформенные; СУБД ждёт вечно

Стандарт 783 называет 20 секунд ожидания блокировки. У обеих СУБД
умолчание противоположное:

- **MS SQL:** «A value of -1 (default) indicates no time-out period (that
  is, wait forever)»; при срабатывании `LOCK_TIMEOUT` возвращается
  «error message 1222 (Lock request time-out period exceeded)»;
- **PostgreSQL:** `lock_timeout` — «A value of zero (the default) disables
  the timeout».

**Вывод набора:** таймаут в 20 секунд, на который опирается вся дисциплина
коротких транзакций, ставит платформа, а не СУБД. Поэтому, во-первых,
сообщение о превышении времени ожидания блокировки — платформенное,
а у SQL Server на этот случай своё, 1222; тексты платформенных сообщений
и то, как по ним отличить конфликт платформы от конфликта СУБД, —
у соседа `1c-quality-gates` (`tech-journal.md`). Во-вторых, запрос, ждущий блокировки
**самой СУБД** — например, на реструктуризации или регламентной операции
вне транзакции 1С, — ограничен не двадцатью секундами, а ничем.

## Взаимоблокировку разрешают по-разному, и на MS SQL на это можно влиять

**MS SQL.** «Deadlock detection is performed by a lock monitor thread that
periodically initiates a search … The default interval is 5 seconds»;
жертва выбирается не случайно: «If two sessions have different deadlock
priorities, the transaction on the session with the lower priority is
chosen as the deadlock victim. If both sessions have the same deadlock
priority, the transaction that is least expensive to roll back is chosen»,
и приложению возвращается «error 1205».

**PostgreSQL.** «PostgreSQL automatically detects deadlock situations and
resolves them by aborting one of the transactions involved», но —
и это важно — «(Exactly which transaction will be aborted is difficult
to predict and should not be relied upon.)» Проверка не мгновенная:
`deadlock_timeout` — «the amount of time to wait on a lock before checking
to see if there is a deadlock condition… The default is one second (1s)».

**Вывод набора.** На SQL Server порядок операций и стоимость отката делают
жертву предсказуемой, а `DEADLOCK_PRIORITY` позволяет назначить её
намеренно; на PostgreSQL ни того, ни другого нет — там помогает только
единый порядок захвата, который и предписывает стандарт 661 (записывать
контролирующие регистры последними, в одинаковом порядке). То есть приём
1С, объяснённый как «предотвращение взаимоблокировки», на PostgreSQL —
единственное доступное средство, а не одно из.

## «Грязное» чтение теряет и дублирует строки, а не только показывает старое

Руководство перечисляет, где безответственное чтение вне транзакции
оказывается «грязным» (§9.2.3.2: файловая база, MS SQL Server 2000,
IBM Db2 до 9.7). Чем это грозит, оно не говорит; документация SQL Server
говорит прямо про `READ UNCOMMITTED`: «Values in the data can be changed
and rows can appear or disappear in the data set before the end of the
transaction».

**Вывод набора:** «грязное» чтение — это не только «увидеть чужое
незафиксированное». Строка может **пропасть из выборки** или попасть
в неё дважды, и отчёт, построенный на таком чтении, не воспроизводится
даже на неизменных данных.

## Что PostgreSQL не защищает версиями: TRUNCATE и перестройка таблицы

PostgreSQL оговаривает границу MVCC: «Some DDL commands, currently only
TRUNCATE and the table-rewriting forms of ALTER TABLE, are not MVCC-safe.
This means that after the truncation or rewrite commits, the table will
appear empty to concurrent transactions, if they are using a snapshot
taken before the DDL command committed».

**Вывод набора:** это ровно те операции, которые платформа выполняет при
реструктуризации и при `/EraseData`. Сеанс, читающий данные в момент
такой операции на PostgreSQL, увидит пустую таблицу вместо ошибки —
и это ещё одна причина требовать монопольного режима, а не надеяться
на изоляцию.

## Чего в документации СУБД нет применительно к 1С

- **соответствия одной управляемой блокировки одной блокировке СУБД.**
  Что **видно**, ИТС описывает и даёт этому инструмент: элемент
  `<dbmslocks>` включает сбор пар «жертва — источник» на стороне СУБД
  (руководство администратора, §3.24.5; разбор — у соседа
  `1c-quality-gates`, `tech-journal-dbms.md`). Но это пары **соединений
  и запросов к СУБД**, а не перевод пространства блокировки 1С в объект
  блокировки SQL Server: такого перевода не публикует ни одна сторона,
  и в управляемом режиме сама платформа держит блокировки у себя, оставляя
  СУБД Read Committed (§9.2.3.2);
- **отличий сборок PostgreSQL «…1C»** — патчи 1С документацией
  PostgreSQL не описаны, а ИТС описывает их только там, где даёт
  настройки;
- **чисел под нагрузкой.** Пороги (5000 у MS SQL, 64 объекта
  у PostgreSQL по умолчанию) названы, но во сколько документов и строк
  регистров они превращаются — вопрос замера, а не документации;
- **поведения файлового варианта** — он не СУБД в этом смысле, и здесь
  описан только там, где его называет руководство.
