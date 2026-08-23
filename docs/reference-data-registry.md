# Опись данных референсных наборов (РАЗБОР-1б)

Порождается `tools/build-reference-data-registry.py` из `_ref/` под gitignore.
Навыки описаны отдельно — `docs/reference-registry.md`.

**Решения о судьбе объекта здесь нет и не будет.** Опись отвечает на вопрос
«что есть»; чужой материал не переносится вовсе (решение 16 общего плана).

| Класс | Файлов | Знаков |
|---|---|---|
| docs | 79 | 1574288 |
| rules | 35 | 220959 |
| справочники навыков | 116 | 896184 |
| обвязка | 19 | 147451 |
| скрипты навыков | 338 | 11231632 |
| тесты | 8709 | — |

## docs — 79

| Файл | Набор | Заголовок | Разделов | Знаков | Пара |
|---|---|---|---|---|---|
| `1c-config-objects-spec.md` | cc | Спецификация формата XML объектов метаданных конфигурации 1С | 105 | 65088 | да |
| `1c-configuration-spec.md` | cc | Спецификация корневой структуры конфигурации 1С | 52 | 47723 | да |
| `1c-dcs-spec.md` | cc | Спецификация XML-формата схемы компоновки данных 1С (DCS) | 46 | 35220 | да |
| `1c-epf-spec.md` | cc | Спецификация XML-формата выгрузки внешней обработки 1С | 45 | 28505 | да |
| `1c-erf-spec.md` | cc | Спецификация XML-формата выгрузки внешнего отчёта 1С | 29 | 25080 | да |
| `1c-extension-spec.md` | cc | Спецификация формата выгрузки расширений конфигурации 1С (CFE) | 74 | 44854 | да |
| `1c-form-spec.md` | cc | 1C Form.xml Format Specification | 67 | 43557 | да |
| `1c-help-spec.md` | cc | Встроенная справка внешней обработки 1С | 12 | 5252 | да |
| `1c-role-spec.md` | cc | Спецификация формата ролей 1С:Предприятия 8.3 | 59 | 28968 | да |
| `1c-specs-index.md` | cc | Сводный индекс спецификаций формата XML конфигурации 1С | 15 | 13524 | да |
| `1c-spreadsheet-spec.md` | cc | Спецификация XML-формата табличного документа (SpreadsheetDocument) | 42 | 36102 | да |
| `1c-subsystem-spec.md` | cc | Спецификация формата XML подсистем и командного интерфейса 1С | 58 | 33536 | да |
| `1c-support-state-spec.md` | cc | Состояние поддержки конфигурации 1С — `Ext/ParentConfigurations.bin` | 9 | 9576 | да |
| `1c-xdto-spec.md` | cc | Спецификация формата XML пакетов XDTO 1С | 16 | 12439 | да |
| `build-spec.md` | cc | Пакетный режим конфигуратора 1С | 31 | 13116 | да |
| `cf-guide.md` | cc | Корневые файлы конфигурации | 20 | 6384 | да |
| `cfe-guide.md` | cc | Расширения конфигурации (CFE) | 17 | 7655 | да |
| `db-guide.md` | cc | Базы данных 1С | 15 | 9785 | да |
| `epf-guide.md` | cc | Внешние обработки и отчёты (EPF / ERF) | 15 | 7368 | да |
| `form-dsl-spec.md` | cc | Form DSL Specification | 60 | 91227 | да |
| `form-guide.md` | cc | Управляемые формы (Form) | 19 | 10023 | да |
| `form-patterns.md` | cc | Паттерны компоновки управляемых форм | 20 | 12548 | — |
| `meta-dsl-spec.md` | cc | Meta DSL — спецификация JSON-формата для объектов метаданных 1С | 92 | 92046 | да |
| `meta-guide.md` | cc | Объекты метаданных конфигурации | 18 | 6489 | да |
| `mxl-dsl-spec.md` | cc | Спецификация MXL DSL — JSON-формат описания табличного документа | 31 | 31019 | да |
| `mxl-guide.md` | cc | Табличный документ (MXL) | 10 | 4469 | да |
| `python-porting-guide.md` | cc | Python Porting Guide | 22 | 11716 | да |
| `role-dsl-spec.md` | cc | Спецификация Role JSON DSL | 11 | 3660 | да |
| `role-guide.md` | cc | Роли (Role) | 15 | 4468 | да |
| `skd-dsl-spec.md` | cc | JSON DSL для схемы компоновки данных (СКД) | 69 | 51091 | да |
| `skd-guide.md` | cc | Схема компоновки данных (СКД) | 18 | 9738 | да |
| `subsystem-guide.md` | cc | Подсистемы и командный интерфейс | 18 | 7241 | да |
| `v8-project-guide.md` | cc | Конфигурация проекта (.v8-project.json) | 17 | 13367 | да |
| `web-guide.md` | cc | Веб-публикация 1С | 19 | 4234 | да |
| `web-spec.md` | cc | Веб-публикация 1С — техническая спецификация | 23 | 6345 | да |
| `web-test-guide.md` | cc | Тестирование через веб-клиент 1С | 31 | 21684 | да |
| `web-test-recording-guide.md` | cc | Запись видеоинструкций | 25 | 12137 | да |
| `web-test-regression-guide.md` | cc | Регрессионное тестирование прикладного решения | 25 | 19809 | — |
| `web-test-regression-spec.md` | cc | Регрессионное тестирование — спецификация | 69 | 59403 | — |
| `xdto-dsl-spec.md` | cc | Спецификация XDTO DSL — XML Schema как формат описания пакета | 7 | 9322 | — |
| `xdto-guide.md` | cc | Работа с пакетами XDTO | 14 | 7993 | — |
| `1c-config-objects-spec.md` | ccs | Спецификация формата XML объектов метаданных конфигурации 1С | 106 | 65907 | да |
| `1c-configuration-spec.md` | ccs | Спецификация корневой структуры конфигурации 1С | 53 | 44249 | да |
| `1c-dcs-spec.md` | ccs | Спецификация XML-формата схемы компоновки данных 1С (DCS) | 44 | 33004 | да |
| `1c-epf-spec.md` | ccs | Спецификация XML-формата выгрузки внешней обработки 1С | 45 | 28505 | да |
| `1c-erf-spec.md` | ccs | Спецификация XML-формата выгрузки внешнего отчёта 1С | 29 | 25080 | да |
| `1c-extension-spec.md` | ccs | Спецификация формата выгрузки расширений конфигурации 1С (CFE) | 72 | 40692 | да |
| `1c-form-spec.md` | ccs | 1C Form.xml Format Specification | 65 | 37437 | да |
| `1c-help-spec.md` | ccs | Встроенная справка внешней обработки 1С | 12 | 5252 | да |
| `1c-role-spec.md` | ccs | Спецификация формата ролей 1С:Предприятия 8.3 | 58 | 25942 | да |
| `1c-specs-index.md` | ccs | Сводный индекс спецификаций формата XML конфигурации 1С | 15 | 13344 | да |
| `1c-spreadsheet-spec.md` | ccs | Спецификация XML-формата табличного документа (SpreadsheetDocument) | 32 | 15232 | да |
| `1c-subsystem-spec.md` | ccs | Спецификация формата XML подсистем и командного интерфейса 1С | 58 | 33395 | да |
| `1c-support-state-spec.md` | ccs | Состояние поддержки конфигурации 1С — `Ext/ParentConfigurations.bin` | 9 | 9196 | да |
| `1c-xdto-spec.md` | ccs | Спецификация формата XML пакетов XDTO 1С | 16 | 12439 | да |
| `исходный промпт.md` | ccs | — | 0 | 302 | — |
| `обработанный промпт.md` | ccs | — | 0 | 842 | — |
| `build-spec.md` | ccs | Пакетный режим конфигуратора 1С | 64 | 31516 | да |
| `cf-guide.md` | ccs | Корневые файлы конфигурации | 20 | 6530 | да |
| `cfe-guide.md` | ccs | Расширения конфигурации (CFE) | 15 | 6363 | да |
| `db-guide.md` | ccs | Базы данных 1С | 13 | 4087 | да |
| `epf-guide.md` | ccs | Внешние обработки и отчёты (EPF / ERF) | 15 | 7478 | да |
| `form-dsl-spec.md` | ccs | Form DSL Specification | 35 | 14381 | да |
| `form-guide.md` | ccs | Управляемые формы (Form) | 17 | 9033 | да |
| `meta-dsl-spec.md` | ccs | Meta DSL — спецификация JSON-формата для объектов метаданных 1С | 68 | 33156 | да |
| `meta-guide.md` | ccs | Объекты метаданных конфигурации | 18 | 6489 | да |
| `mxl-dsl-spec.md` | ccs | Спецификация MXL DSL — JSON-формат описания табличного документа | 10 | 5668 | да |
| `mxl-guide.md` | ccs | Табличный документ (MXL) | 10 | 4469 | да |
| `python-porting-guide.md` | ccs | Python Porting Guide | 17 | 7322 | да |
| `role-dsl-spec.md` | ccs | Спецификация Role JSON DSL | 11 | 3666 | да |
| `role-guide.md` | ccs | Роли (Role) | 15 | 4468 | да |
| `skd-dsl-spec.md` | ccs | JSON DSL для схемы компоновки данных (СКД) | 51 | 22003 | да |
| `skd-guide.md` | ccs | Схема компоновки данных (СКД) | 16 | 6161 | да |
| `subsystem-guide.md` | ccs | Подсистемы и командный интерфейс | 18 | 7241 | да |
| `v8-project-guide.md` | ccs | Конфигурация проекта (.v8-project.json) | 12 | 7349 | да |
| `web-guide.md` | ccs | Веб-публикация 1С | 19 | 4234 | да |
| `web-spec.md` | ccs | Веб-публикация 1С — техническая спецификация | 22 | 4901 | да |
| `web-test-guide.md` | ccs | Тестирование через веб-клиент 1С | 29 | 12639 | да |
| `web-test-recording-guide.md` | ccs | Запись видеоинструкций | 24 | 10555 | да |

## rules — 35

| Файл | Набор | Заголовок | Разделов | Знаков | Пара |
|---|---|---|---|---|---|
| `1c-coding-standards.md` | ccs | 1C Coding Standards | 37 | 23530 | — |
| `1c-extension-patterns.md` | ccs | 1C Extension Patterns (CFE) | 12 | 3953 | — |
| `1c-form-reserved-names.md` | ccs | Зарезервированные имена в модулях форм 1С | 6 | 3463 | — |
| `1c-mdo-integrity.md` | ccs | 1C MDO Integrity Rules | 13 | 6230 | — |
| `1c-report-direct-query.md` | ccs | Формирование отчёта 1С через прямое выполнение запроса (без СКД-движка) | 4 | 6237 | — |
| `1c-role-rights.md` | ccs | 1C Role Rights — правила прав в ролях | 6 | 2722 | — |
| `1c-skd-two-pass-preprocessing.md` | ccs | Двухпроходный СКД: предобработка деталей до свёртки | 3 | 4988 | — |
| `agent-verification-patterns.md` | ccs | Agent Verification Patterns | 8 | 2987 | — |
| `agent-working-memory.md` | ccs | Рабочая память агента: файлы плана, передача сессии, журнал инцидентов | 4 | 3991 | — |
| `anti_patterns.md` | ccs | Анти-паттерны и рекомендации по производительности 1С | 16 | 9681 | — |
| `async-methods-1c.md` | ccs | Асинхронные методы 1С (Асинх / Ждать / Обещание) | 12 | 6118 | — |
| `bsl-ssl.md` | ccs | Работа с БСП (Библиотека стандартных подсистем) | 13 | 9306 | — |
| `bsp-profile-rights-api.md` | ccs | Программная работа с профилями групп доступа БСП | 9 | 10371 | — |
| `code-exploration-guide.md` | ccs | 1C Code Exploration Guide | 13 | 5162 | — |
| `code-review-checklist.md` | ccs | 1C Code Review Checklist | 11 | 3140 | — |
| `edt-bsl-write-safety.md` | ccs | Безопасная запись BSL через write_module_source | 8 | 5243 | — |
| `edt-form-xml-requirements.md` | ccs | Требования EDT к XML-формам (Form.form) | 20 | 9715 | — |
| `edt-zip-export-pitfalls.md` | ccs | EDT Zip Export Pitfalls | 15 | 6617 | — |
| `external-data-source-mdo.md` | ccs | ExternalDataSource MDO Format (EDT) | 20 | 8709 | — |
| `file-edit-efficiency.md` | ccs | File Edit Efficiency | 8 | 3804 | — |
| `form_module_rules.md` | ccs | Правила работы с модулями форм 1С | 5 | 1459 | — |
| `forms_events.md` | ccs | Добавление обработчиков событий на форму 1С | 1 | 1270 | — |
| `forms_generation.md` | ccs | Генерация и модификация форм 1С | 5 | 2968 | — |
| `git-safety-rules.md` | ccs | Git Safety Rules | 17 | 6549 | — |
| `integrations.md` | ccs | Integrations — Python-first подход | 4 | 1209 | — |
| `mcp-tool-priority.md` | ccs | MCP Tool Priority for 1C/BSL | 8 | 18870 | — |
| `model-selection.md` | ccs | Стратегия выбора моделей | 12 | 8745 | — |
| `query-optimization-tips.md` | ccs | 1C Query Optimization Tips | 9 | 6324 | — |
| `refactoring.md` | ccs | Правила рефакторинга 1С | 10 | 3156 | — |
| `routine_assignment_ext_processor.md` | ccs | Фоновые задания из внешней обработки (БСП) | 5 | 3461 | — |
| `sdd-workflow.md` | ccs | Specification-Driven Development (SDD) | 17 | 8212 | — |
| `skill-design.md` | ccs | Проектирование скилов | 7 | 4877 | — |
| `testing-patterns.md` | ccs | 1C Testing Patterns | 10 | 2590 | — |
| `text-formatting.md` | ccs | Text Formatting | 3 | 4249 | — |
| `v8unpack-source-structure.md` | ccs | Структура исходников v8unpack | 31 | 11053 | — |

## Семейства тестовых случаев — 137

По решению 16 берётся только структура: чужой код не переносится, а знать
надо, какая возможность проверяется, а не как написан случай.

| Семейство | Набор | Файлов | Форматы |
|---|---|---|---|
| `cf-edit` | cc | 106 | .bin, .bsl, .json, .xml |
| `cf-info` | cc | 33 | .bsl, .json, .xml |
| `cf-init` | cc | 46 | .json, .xml |
| `cf-validate` | cc | 21 | .json, .xml |
| `cfe-borrow` | cc | 546 | .bsl, .json, .xml |
| `cfe-diff` | cc | 40 | .bin, .bsl, .json, .xml |
| `cfe-init` | cc | 49 | .json, .xml |
| `cfe-patch-method` | cc | 240 | .bsl, .json, .xml |
| `cfe-validate` | cc | 93 | .bsl, .json, .xml |
| `db-create` | cc | 14 | .json |
| `db-dump-cf` | cc | 4 | .json |
| `db-dump-dt` | cc | 2 | .json |
| `db-dump-xml` | cc | 3 | .json |
| `db-load-cf` | cc | 3 | .json |
| `db-load-dt` | cc | 2 | .json |
| `db-load-git` | cc | 3 | .json |
| `db-load-xml` | cc | 12 | .json |
| `db-run` | cc | 4 | .json |
| `db-update` | cc | 11 | .json |
| `epf-build` | cc | 5 | .json |
| `epf-dump` | cc | 3 | .json |
| `epf-init` | cc | 20 | .bsl, .json, .xml |
| `epf-validate` | cc | 20 | .bsl, .json, .xml |
| `erf-init` | cc | 18 | .bsl, .json, .xml |
| `erf-validate` | cc | 4 | .bsl, .json, .xml |
| `form-add` | cc | 185 | .bin, .bsl, .json, .xml |
| `form-compile` | cc | 339 | .bin, .bsl, .json, .xml |
| `form-compile-from-object` | cc | 116 | .bsl, .json, .xml |
| `form-decompile` | cc | 13 | .bsl, .json, .xml |
| `form-edit` | cc | 59 | .bin, .bsl, .json, .xml |
| `form-info` | cc | 33 | .bsl, .json, .xml |
| `form-remove` | cc | 67 | .bsl, .json, .xml |
| `form-validate` | cc | 177 | .bsl, .json, .xml |
| `help-add` | cc | 34 | .bin, .bsl, .html, .json, .xml |
| `interface-edit` | cc | 57 | .bin, .bsl, .json, .xml |
| `interface-validate` | cc | 21 | .bsl, .json, .xml |
| `meta-compile` | cc | 526 | .bin, .bsl, .json, .xml |
| `meta-decompile` | cc | 10 | .bsl, .json, .xml |
| `meta-edit` | cc | 148 | .bin, .bsl, .json, .xml |
| `meta-info` | cc | 110 | .bsl, .json, .xml |
| `meta-remove` | cc | 47 | .bin, .bsl, .json, .xml |
| `meta-validate` | cc | 142 | .bsl, .json, .xml |
| `mxl-compile` | cc | 142 | .bin, .json, .xml |
| `mxl-decompile` | cc | 43 | .json, .xml |
| `mxl-info` | cc | 21 | .bin, .json, .xml |
| `mxl-validate` | cc | 25 | .json, .xml |
| `role-compile` | cc | 177 | .bin, .bsl, .json, .xml |
| `role-info` | cc | 34 | .bsl, .json, .xml |
| `role-validate` | cc | 39 | .bsl, .json, .xml |
| `skd-compile` | cc | 64 | .bin, .json, .xml |
| `skd-decompile` | cc | 55 | .json, .sql, .xml |
| `skd-edit` | cc | 105 | .bin, .json, .xml |
| `skd-info` | cc | 19 | .json, .txt, .xml |
| `skd-validate` | cc | 29 | .json, .xml |
| `subsystem-compile` | cc | 74 | .bin, .bsl, .json, .xml |
| `subsystem-edit` | cc | 82 | .bin, .bsl, .json, .xml |
| `subsystem-info` | cc | 33 | .bsl, .json, .xml |
| `subsystem-validate` | cc | 25 | .bsl, .json, .xml |
| `support-edit` | cc | 30 | .bin, .json, .xml |
| `template-add` | cc | 45 | .bin, .bsl, .html, .json, .txt, .xml |
| `template-remove` | cc | 8 | .bsl, .json, .xml |
| `xdto-compile` | cc | 107 | .bin, .json, .xml, .xsd |
| `xdto-decompile` | cc | 46 | .bin, .json, .xml, .xsd |
| `xdto-edit` | cc | 80 | .bin, .json, .xml, .xsd |
| `xdto-info` | cc | 92 | .bin, .json, .txt, .xml, .xsd |
| `xdto-validate` | cc | 24 | .bin, .json, .xml, .xsd |
| `bsl-validate` | ccs | 12 | .json |
| `bsp-api` | ccs | 15 | .json |
| `cf-edit` | ccs | 98 | .bin, .bsl, .json, .xml |
| `cf-info` | ccs | 29 | .bsl, .json, .xml |
| `cf-init` | ccs | 46 | .json, .xml |
| `cf-validate` | ccs | 19 | .json, .xml |
| `cfe-borrow` | ccs | 185 | .bsl, .json, .xml |
| `cfe-diff` | ccs | 36 | .bin, .bsl, .json, .xml |
| `cfe-init` | ccs | 44 | .json, .xml |
| `cfe-patch-method` | ccs | 229 | .bsl, .json, .xml |
| `cfe-validate` | ccs | 26 | .bsl, .json, .xml |
| `config-index` | ccs | 63 | .bsl, .json, .txt, .xml |
| `db-create` | ccs | 14 | .json |
| `db-dump-cf` | ccs | 4 | .json |
| `db-dump-dt` | ccs | 2 | .json |
| `db-dump-xml` | ccs | 3 | .json |
| `db-load-cf` | ccs | 3 | .json |
| `db-load-dt` | ccs | 2 | .json |
| `db-load-git` | ccs | 3 | .json |
| `db-load-xml` | ccs | 12 | .json |
| `db-run` | ccs | 4 | .json |
| `db-update` | ccs | 11 | .json |
| `epf-build` | ccs | 5 | .json |
| `epf-dump` | ccs | 3 | .json |
| `epf-init` | ccs | 20 | .bsl, .json, .xml |
| `epf-validate` | ccs | 20 | .bsl, .json, .xml |
| `erf-init` | ccs | 18 | .bsl, .json, .xml |
| `erf-validate` | ccs | 4 | .bsl, .json, .xml |
| `form-add` | ccs | 97 | .bin, .bsl, .json, .xml |
| `form-compile` | ccs | 339 | .bin, .bsl, .json, .xml |
| `form-compile-from-object` | ccs | 114 | .bsl, .json, .xml |
| `form-decompile` | ccs | 13 | .bsl, .json, .xml |
| `form-edit` | ccs | 59 | .bin, .bsl, .json, .xml |
| `form-info` | ccs | 33 | .bsl, .json, .xml |
| `form-remove` | ccs | 8 | .bsl, .json, .xml |
| `form-validate` | ccs | 179 | .bsl, .json, .xml |
| `help-add` | ccs | 33 | .bin, .bsl, .html, .json, .xml |
| `humanize-scan` | ccs | 10 | .json, .md |
| `interface-edit` | ccs | 42 | .bin, .bsl, .json, .xml |
| `interface-validate` | ccs | 19 | .bsl, .json, .xml |
| `meta-compile` | ccs | 481 | .bin, .bsl, .json, .xml |
| `meta-decompile` | ccs | 10 | .bsl, .json, .xml |
| `meta-edit` | ccs | 133 | .bin, .bsl, .json, .xml |
| `meta-info` | ccs | 103 | .bsl, .json, .xml |
| `meta-remove` | ccs | 27 | .bin, .bsl, .json, .xml |
| `meta-validate` | ccs | 76 | .bsl, .json, .xml |
| `mxl-compile` | ccs | 91 | .bin, .json, .xml |
| `mxl-decompile` | ccs | 16 | .json, .xml |
| `mxl-info` | ccs | 21 | .bin, .json, .xml |
| `mxl-validate` | ccs | 16 | .json, .xml |
| `query-validate` | ccs | 10 | .json |
| `role-compile` | ccs | 117 | .bin, .bsl, .json, .xml |
| `role-info` | ccs | 34 | .bsl, .json, .xml |
| `role-validate` | ccs | 39 | .bsl, .json, .xml |
| `skd-compile` | ccs | 64 | .bin, .json, .xml |
| `skd-decompile` | ccs | 55 | .json, .sql, .xml |
| `skd-edit` | ccs | 103 | .bin, .json, .xml |
| `skd-info` | ccs | 19 | .json, .txt, .xml |
| `skd-validate` | ccs | 31 | .json, .xml |
| `subsystem-compile` | ccs | 66 | .bin, .bsl, .json, .xml |
| `subsystem-edit` | ccs | 77 | .bin, .bsl, .json, .xml |
| `subsystem-info` | ccs | 29 | .bsl, .json, .xml |
| `subsystem-validate` | ccs | 24 | .bsl, .json, .xml |
| `support-edit` | ccs | 30 | .bin, .json, .xml |
| `template-add` | ccs | 45 | .bin, .bsl, .html, .json, .txt, .xml |
| `template-remove` | ccs | 8 | .bsl, .json, .xml |
| `xdto-compile` | ccs | 97 | .bin, .json, .xml, .xsd |
| `xdto-decompile` | ccs | 41 | .bin, .json, .xml, .xsd |
| `xdto-edit` | ccs | 78 | .bin, .json, .xml, .xsd |
| `xdto-info` | ccs | 83 | .bin, .json, .txt, .xml, .xsd |
| `xdto-validate` | ccs | 24 | .bin, .json, .xml, .xsd |

