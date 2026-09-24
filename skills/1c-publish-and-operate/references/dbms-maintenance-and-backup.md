# Обслуживание и копирование СУБД под 1С: где рецепт ИТС отстал от СУБД

**Ищут по словам:** регламентные операции СУБД, обновление статистики,
`UPDATE STATISTICS`, `DBCC FREEPROCCACHE`, очистка процедурного кэша,
`DBCC INDEXDEFRAG`, `DBCC DBREINDEX`, `ALTER INDEX REBUILD`, дефрагментация
индексов, реиндексация, `VACUUM`, `VACUUM FULL`, автовакуум, распухание
таблиц, `ANALYZE`, `REINDEX`, модель восстановления, журнал транзакций,
`pg_dump`, PITR, восстановление на момент времени, архивирование WAL.

**Источники.** Методические материалы ИТС — «Регламентные операции
на уровне СУБД для MS SQL Server» (методичка 5837); руководство
администратора (разбор копирования — в `backup-and-restore.md`);
документация PostgreSQL 17 и Microsoft Learn по SQL Server
(view=sql-server-ver16).

**Поведение СУБД здесь описано по документации и запуском не проверено**
(решение 24). Сборки PostgreSQL «…1C» несут патчи 1С, которых документация
PostgreSQL не описывает.

**Спина разбора: рецепт ИТС верен по смыслу и устарел в командах.**
Методичка 5837 настраивает план обслуживания «для MS SQL Server 2005»;
две из четырёх названных в ней команд Microsoft объявила подлежащими
удалению, а третью велит применять осторожно. Для PostgreSQL готового
рецепта в ИТС нет вовсе — там работает свой механизм, о котором стандарты
1С не говорят.

## Что предписывает ИТС для MS SQL

Методичка 5837 называет четыре операции: «Обновление статистик Очистка
процедурного КЭШа Дефрагментация индексов Реиндексация таблиц базы
данных», требует их автоматизировать и добавляет мотив: «Одной из часто
встречающихся причин неоптимальной работы системы является неправильное
или несвоевременное выполнение регламентных операций на уровне СУБД».

Два числа и два утверждения оттуда же: «Рекомендуется обновлять статистики
не реже одного раза в день», «Обновление статистик не приводит
к блокировке таблиц, и не будет мешать работе других пользователей».

## Две команды из рецепта помечены на удаление

**`DBCC INDEXDEFRAG`** (в методичке — «Дефрагментация индексов»):
«This feature will be removed in a future version of SQL Server. Avoid
using this feature in new development work, and plan to modify applications
that currently use this feature. Use ALTER INDEX instead.»

**`DBCC DBREINDEX`** (в методичке — «Реиндексация таблиц»): то же
предупреждение дословно, и тоже «Use ALTER INDEX instead».

**Вывод набора, а не источника.** Смысл операций остаётся: фрагментация
индексов лечится, реиндексация нужна. Меняются команды —
`ALTER INDEX … REORGANIZE` и `ALTER INDEX … REBUILD` вместо двух `DBCC`.
Копировать план обслуживания из методички как есть нельзя: он написан
под SQL Server 2005, и это сказано в ней самой («Настройка автоматического
обновления статистик (MS SQL 2005)»).

## Очистка кэша планов — не безобидная гигиена

Методичка предписывает `DBCC FREEPROCCACHE` **после каждого** обновления
статистики: «Этот запрос следует выполнять непосредственно после обновления
статистики. Соответственно, частота его выполнения должна совпадать
с частотой обновления статистики».

Microsoft описывает цену:

> «Use DBCC FREEPROCCACHE to clear the plan cache carefully. Clearing the
> procedure (plan) cache causes all plans to be evicted, and incoming query
> executions will compile a new plan, instead of reusing any previously
> cached plan. This can cause a sudden, temporary decrease in query
> performance as the number of new compilations increases.»

**Вывод набора.** Обе стороны правы в своём: 1С лечит планы, построенные
по устаревшей статистике, Microsoft предупреждает, что лечение бьёт
по всему серверу сразу. Поэтому операция уместна ночью, вместе
с обновлением статистики, и неуместна днём «на всякий случай»; на сервере,
где кроме базы 1С живут чужие базы, она задевает и их — кэш планов общий
для экземпляра.

## У PostgreSQL другой набор работ, и часть выполняется сама

Готовой методички ИТС по PostgreSQL в корпусе нет; документация
PostgreSQL называет четыре причины для `VACUUM`: «To recover or reuse disk
space occupied by updated or deleted rows. To update data statistics used
by the PostgreSQL query planner. To update the visibility map, which speeds
up index-only scans. To protect against loss of very old data due to
transaction ID wraparound or multixact ID wraparound».

Что отсюда важно для 1С:

- **обычно это делается само:** «For many installations, it is sufficient
  to let vacuuming be performed by the autovacuum daemon»; статистику
  обновляет он же — «The autovacuum daemon, if enabled, will automatically
  issue ANALYZE commands whenever the content of a table has changed
  sufficiently». Аналога ежедневного `UPDATE STATISTICS … WITH FULLSCAN`
  из методички 5837 здесь не требуется;
- **`VACUUM FULL` — не «более тщательный вакуум», а другая операция:**
  «VACUUM FULL can reclaim more disk space but runs much more slowly.
  Also, the standard form of VACUUM can run in parallel with production
  database operations». **Вывод набора:** обычный `VACUUM` рабочей базе
  не мешает, `VACUUM FULL` — операция окна обслуживания;
- **реиндексация нужна и здесь, но по другой причине:** «B-tree index
  pages that have become completely empty are reclaimed for re-use.
  However, there is still a possibility of inefficient use of space: if all
  but a few index keys on a page have been deleted, the page remains
  allocated»;
- **после восстановления копии статистики нет:** «After restoring a backup,
  it is wise to run ANALYZE on each database so the query optimizer has
  useful statistics». Тестовая база, поднятая из копии, будет работать
  «не как бой» именно поэтому.

## Копия СУБД и восстановление на момент времени

Набор уже говорит, что копия средствами СУБД не включает журнал
регистрации и хранилище двоичных данных (`backup-and-restore.md`).
Документация СУБД добавляет то, чего нет в ИТС.

**PostgreSQL: логическая выгрузка и PITR — разные вещи, и одно не заменяет
другое.** `pg_dump` даёт согласованный снимок и не мешает работе:
«dumps created by pg_dump are internally consistent, meaning, the dump
represents a snapshot of the database at the time pg_dump began running.
pg_dump does not block other operations on the database while it is
working». Но для восстановления на произвольный момент нужен другой
механизм: «pg_dump and pg_dumpall do not produce file-system-level backups
and cannot be used as part of a continuous-archiving solution. Such dumps
are logical and do not contain enough information to be used by WAL
replay». Непрерывное архивирование даёт то, чего логическая выгрузка
не даёт: «it is possible to restore the database to its state at any time
since your base backup was taken».

**Вывод набора:** вопрос о том, хватает ли ночной копии или нужен откат
на произвольную минуту, решается до выбора инструмента, а не после: `pg_dump` второй задачи
не решает в принципе, сколько его ни настраивай.

**SQL Server: журнал транзакций растёт, пока его не скопировали.**
Модель восстановления решает и то, и другое: «A recovery model is
a database property that controls how transactions are logged, whether the
transaction log requires (and allows) backing up, and what kinds of restore
operations are available». У полной модели цена названа прямо: «The full
recovery model requires transaction log backups… In this recovery model,
the transaction log continues to grow until you perform a transaction log
backup», а взамен — «You can recover to an arbitrary point in time».
У простой модели обратный размен: «The simple recovery model doesn't
support transaction log backups. The Database Engine automatically reclaims
log space to keep space requirements low».

И умолчание, из-за которого это встречается на бою: «SQL Server Enterprise
and Standard editions use the full recovery model by default».

**Вывод набора:** база 1С на SQL Server по умолчанию оказывается в полной
модели, и если резервируют только базу, а журнал — нет, журнал транзакций
растёт, пока не кончится диск. Это не ошибка настройки 1С и не видно
из платформы: ни один инструмент кластера об этом не сообщает.

## Чего нет ни в ИТС, ни в документации СУБД

- **рецепта регламентных операций для PostgreSQL под 1С.** Документация
  PostgreSQL описывает механизм вообще, ИТС — настройки конкретных сборок;
  сведённого «делайте это и это по расписанию» для базы 1С нет;
- **порогов фрагментации для баз 1С:** когда `REORGANIZE`, а когда
  `REBUILD`, методичка 5837 не говорит, а общие пороги документации
  не привязаны к структуре таблиц 1С;
- **проверки, что регламентные операции идут.** Методичка требует
  «регулярно контролировать своевременность и правильность выполнения»,
  но ни признака в журнале 1С, ни готового запроса не даёт;
- **отличий сборок PostgreSQL «…1C»** — в том числе того, меняют ли патчи
  1С поведение автовакуума.
