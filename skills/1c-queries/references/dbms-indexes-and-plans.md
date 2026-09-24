# Индексы и планы на уровне СУБД: чем правило 1С точнее и чем оно грубее

**Ищут по словам:** индекс не используется, составной индекс, порядок полей
индекса, `ПОДОБНО` и индекс, `LIKE` и индекс, `text_pattern_ops`, локаль
базы PostgreSQL, класс операторов, включённые поля, `INCLUDE`, план запроса,
`EXPLAIN`, статистика, устаревшая статистика, параметры запроса,
parameter sniffing, почему один и тот же запрос то быстрый, то медленный.

**Источники.** Стандарты 652, 658, 791 (разбор — в `query-rules.md`);
документация PostgreSQL 17 и Microsoft Learn по SQL Server
(view=sql-server-ver16); методические материалы ИТС.

**Поведение СУБД здесь описано по документации и запуском не проверено**
(решение 24). Сборки PostgreSQL «…1C» несут патчи 1С, которых документация
PostgreSQL не описывает.

**Спина разбора: стандарт 658 даёт безопасное правило, а СУБД —
более сложную правду в обе стороны.** Где-то индекс сработает и без
выполнения требований стандарта, а где-то не сработает при их выполнении.
Первое делает правило строже нужного и это дёшево; второе опасно, и таких
мест два: `ПОДОБНО` в PostgreSQL и разные планы на одном и том же запросе.

## Требование «поля подряд и с начала» строже, чем правило СУБД

Стандарт 658 требует, чтобы поля условия стояли в начале индекса, подряд
и все. PostgreSQL описывает своё правило мягче и точнее:

> «A multicolumn B-tree index can be used with query conditions that involve
> any subset of the index's columns, but the index is most efficient when
> there are constraints on the leading (leftmost) columns. The exact rule is
> that equality constraints on leading columns, plus any inequality
> constraints on the first column that does not have an equality constraint,
> will be used to limit the portion of the index that is scanned.»

Пересказ: индекс годится для **любого подмножества** своих полей, но
сужает просмотр только по ведущим полям с равенством плюс первое поле
с неравенством; остальные условия проверяются уже по найденным строкам.
То есть стандарт 1С описывает не «когда индекс используется», а «когда
он используется **с пользой**», и как безопасное правило он верен.

У SQL Server та же логика выражена через ключевые и включённые поля:
«If a column must be retrieved by a query, but isn't used in the query
predicates, aggregations, and sorts, add it as an included column and not
as a key column», и включённые поля «aren't considered by the Database
Engine when calculating the number of index key columns or index key
size».

**Вывод набора, а не источника.** Отсюда практическое следствие для
дополнительных индексов 1С (std791): поля, которые нужны запросу только
как результат, кладут в «Дополнительные поля» индекса, а не в ключевые, —
это не украшение, а разные части структуры с разными ограничениями.
И обратное: если поле условия не влезло в ведущие, индекс всё равно может
быть выбран — доказательством служит план, а не рассуждение.

## `ПОДОБНО 'текст%'` в PostgreSQL ложится на индекс не всегда

Стандарт 658 разрешает `ПОДОБНО` на последнем поле индекса при условии,
что литерал не начинается с `_` или `%`. PostgreSQL добавляет второе
условие, которого в стандарте нет:

> «The optimizer can also use a B-tree index for queries involving the
> pattern matching operators LIKE and ~ if the pattern is a constant and is
> anchored to the beginning of the string — for example, col LIKE 'foo%' or
> col ~ '^foo', but not col LIKE '%bar'. However, if your database does not
> use the C locale you will need to create the index with a special operator
> class to support indexing of pattern-matching queries.»

Класс операторов назван там же: «The operator classes text_pattern_ops,
varchar_pattern_ops, and bpchar_pattern_ops support B-tree indexes on the
types text, varchar, and char respectively… This makes these operator
classes suitable for use by queries involving pattern matching expressions»;
и обратная оговорка — «If you do use the C locale, you do not need the
xxx _pattern_ops operator classes» (пробел в «xxx _pattern_ops» —
из выгрузки страницы, в документации там знак подстановки).

**Локаль базы под 1С обычно не C.** Методические материалы ИТС показывают
инициализацию кластера с русской локалью: «The database cluster will be
initialized with locales COLLATE: ru_RU.UTF-8 CTYPE: ru_RU.UTF-8»
(методичка 5971, пример развёртывания дополнительного кластера).

**Вывод набора, а не источника — и граница знания.** На PostgreSQL
с русской локалью обычный индекс поиску по шаблону не помогает, а создаёт
ли платформа индексы со специальным классом операторов, ни ИТС,
ни документация PostgreSQL не говорят. Поэтому: правило стандарта 658
про начало литерала — необходимое условие, но на PostgreSQL его мало,
и единственный честный способ узнать — посмотреть план (`EXPLAIN`).
У SQL Server такого условия нет: там поведение определяет collation
столбца, а не отдельный класс операторов.

## Один и тот же запрос может получить разные планы

Стандарты 1С пишут о запросе так, будто план у него один. У обеих СУБД это
не так, и причина в параметрах.

**SQL Server** называет это прямо: «Parameter sensitivity, also known as
"parameter sniffing", refers to a process whereby SQL Server "sniffs" the
current parameter values during compilation or recompilation, and passes it
along to the Query Optimizer so that they can be used to generate
potentially more efficient query execution plans».

**Вывод набора:** платформа передаёт значения отбора параметрами
(std652 и виртуальные таблицы), то есть попадает ровно в этот механизм.
Один и тот же отчёт, запущенный сперва по редкому складу, а потом по всей
номенклатуре, может выполняться по плану, выбранному для первого случая:
разброс времени при неизменном коде объясняется этим, а не нагрузкой.

## Статистика устаревает по порогу, и порог назван

SQL Server описывает, когда план перестраивается по изменению данных:
«Up to SQL Server 2014 (12.x), the Database Engine uses a recompilation
threshold based on the number of rows in the table or indexed view at the
time statistics were evaluated», и для постоянных таблиц при более чем
500 строках порог — «500 + (0.20 * n)».

И предупреждение о выключенной автообновляемой статистике: «Setting
AUTO_UPDATE_STATISTICS to OFF can cause suboptimal query plans and degraded
query performance».

**Вывод набора:** жалоба на то, что запрос стал медленным без правки
кода, — это в первую очередь вопрос статистики и плана, а не текста запроса;
проверка дешевле догадки, и смотреть надо план на рабочих данных.

## Чего в стандартах нет, а в документации СУБД есть

- **плана запроса как инструмента.** Ни 652, ни 658 не называют `EXPLAIN`
  и «Показать фактический план выполнения»; вся проверка «ложится ли
  условие на индекс» в стандартах — рассуждение по тексту запроса.
  У PostgreSQL этому посвящён отдельный раздел (14.1. Using EXPLAIN),
  у SQL Server — руководство по обработке запросов;
- **того, что индекс — не единственный способ.** Обе СУБД умеют
  сканирование с фильтром, соединения хешем и слиянием, и для маленькой
  таблицы это быстрее поиска по индексу; порог std658 «менее 1000
  записей» — грубое приближение того же соображения.

## Чего нет и в документации СУБД

- **отличий сборок PostgreSQL «…1C»**: какие патчи внесены и меняют ли они
  выбор плана;
- **того, какие индексы создаёт платформа** и с какими классами
  операторов: ИТС перечисляет индексы по смыслу (по ссылке,
  по регистратору, по измерениям), но не в терминах СУБД;
- **соответствия конструкций языка запросов 1С операторам SQL**: во что
  превращается `В ИЕРАРХИИ`, `ДЛЯ ИЗМЕНЕНИЯ` или виртуальная таблица,
  не описано ни там, ни там; это видно только по тексту запроса
  в технологическом журнале (`DBMSSQL`, `DBPOSTGRS`).
