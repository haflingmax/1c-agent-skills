# Опись референсных наборов (ПЕРЕНОС-1)

Порождается `tools/build-transfer-registry.py` из `_ref/` под gitignore.
Правится не руками, а пересборкой.

**Только механический слой.** Выжимка содержания, отнесение к одному из
16 наших разделов и решение «переносить или нет» здесь намеренно
отсутствуют: владелец просил решать попунктно на этапе ПЕРЕНОС-2.

## Источники

| Набор | Автор | Лицензия | Навыков | Ревизия | Дата |
|---|---|---|---|---|---|
| [cc-1c-skills](https://github.com/Nikolay-Shirokov/cc-1c-skills) | Николай Широков | MIT | 77 | `0442aa0` | 2026-08-22 |
| [claude-code-skills-1c](https://github.com/Desko77/claude-code-skills-1c) | Desko77 | MIT | 116 | `35bc5c5` | 2026-08-21 |

## Счёт

Навыков всего: **193**. Из них состоят в паре: **142** (71 пар).
Различных навыков — **122**.

Пара — это две версии одного навыка. `claude-code-skills-1c` производен
от `cc-1c-skills`: его `CHANGELOG.md` ссылается на первый набор и на
`va-ai` того же автора. Имена спариваются по правилу «`X` ↔ `1c-X`».
Разбирать пару надо вместе, сравнивая версии, а не дважды по отдельности.

## cc-1c-skills (77)

| Навык | Знаков | Строк тела | Справочник | Скриптов | Проверок | Пара |
|---|---|---|---|---|---|---|
| `cf-edit` | 2645 | 37 | 5592 зн. | 2 | 0 | `1c-cf-edit` |
| `cf-info` | 1665 | 32 | нет | 2 | 0 | `1c-cf-info` |
| `cf-init` | 2411 | 41 | нет | 2 | 0 | `1c-cf-init` |
| `cf-validate` | 1238 | 14 | нет | 2 | 0 | `1c-cf-validate` |
| `cfe-borrow` | 5413 | 68 | нет | 2 | 0 | `1c-cfe-borrow` |
| `cfe-diff` | 1938 | 33 | нет | 2 | 0 | `1c-cfe-diff` |
| `cfe-init` | 2865 | 43 | нет | 2 | 0 | `1c-cfe-init` |
| `cfe-patch-method` | 8048 | 99 | нет | 2 | 0 | `1c-cfe-patch-method` |
| `cfe-validate` | 1934 | 22 | нет | 2 | 0 | `1c-cfe-validate` |
| `db-create` | 2677 | 43 | нет | 2 | 0 | `1c-db-create` |
| `db-dump-cf` | 2873 | 45 | нет | 2 | 0 | `1c-db-dump-cf` |
| `db-dump-dt` | 3024 | 47 | нет | 2 | 0 | `1c-db-dump-dt` |
| `db-dump-xml` | 4297 | 62 | нет | 2 | 0 | `1c-db-dump-xml` |
| `db-list` | 5096 | 116 | нет | 0 | 0 | `1c-db-list` |
| `db-load-cf` | 3066 | 47 | нет | 2 | 0 | `1c-db-load-cf` |
| `db-load-dt` | 3914 | 60 | нет | 2 | 0 | `1c-db-load-dt` |
| `db-load-git` | 3540 | 53 | нет | 2 | 0 | `1c-db-load-git` |
| `db-load-xml` | 4542 | 69 | нет | 2 | 0 | `1c-db-load-xml` |
| `db-run` | 2934 | 49 | нет | 2 | 0 | `1c-db-run` |
| `db-update` | 3584 | 59 | нет | 2 | 0 | `1c-db-update` |
| `epf-bsp-add-command` | 7497 | 131 | нет | 0 | 0 | — |
| `epf-bsp-init` | 7729 | 129 | нет | 0 | 0 | — |
| `epf-build` | 3332 | 45 | нет | 4 | 0 | `1c-epf-build` |
| `epf-dump` | 3274 | 45 | нет | 2 | 0 | `1c-epf-dump` |
| `epf-init` | 1893 | 26 | нет | 2 | 0 | — |
| `epf-validate` | 1334 | 14 | нет | 2 | 0 | `1c-epf-validate` |
| `erf-build` | 3331 | 46 | нет | 0 | 0 | `1c-erf-build` |
| `erf-dump` | 3293 | 46 | нет | 0 | 0 | `1c-erf-dump` |
| `erf-init` | 1979 | 27 | нет | 2 | 0 | `1c-erf-init` |
| `erf-validate` | 1441 | 15 | нет | 0 | 0 | `1c-erf-validate` |
| `form-add` | 3782 | 61 | нет | 2 | 0 | `1c-form-add` |
| `form-compile` | 23816 | 452 | нет | 2 | 0 | `1c-form-compile` |
| `form-decompile` | 2119 | 23 | нет | 2 | 0 | `1c-form-decompile` |
| `form-edit` | 4732 | 101 | нет | 2 | 0 | `1c-form-edit` |
| `form-info` | 985 | 14 | нет | 2 | 0 | `1c-form-info` |
| `form-patterns` | 8656 | 193 | нет | 0 | 0 | `1c-form-patterns` |
| `form-remove` | 1444 | 24 | нет | 2 | 0 | `1c-form-remove` |
| `form-validate` | 1186 | 13 | нет | 2 | 0 | `1c-form-validate` |
| `help-add` | 1678 | 21 | нет | 2 | 0 | — |
| `img-grid` | 2753 | 47 | нет | 1 | 0 | — |
| `interface-edit` | 2360 | 46 | нет | 2 | 0 | `1c-interface-edit` |
| `interface-validate` | 1212 | 14 | нет | 2 | 0 | `1c-interface-validate` |
| `meta-compile` | 5672 | 97 | нет | 2 | 0 | `1c-meta-compile` |
| `meta-decompile` | 3063 | 26 | нет | 2 | 0 | `1c-meta-decompile` |
| `meta-edit` | 4664 | 73 | нет | 2 | 0 | `1c-meta-edit` |
| `meta-info` | 3595 | 56 | нет | 2 | 0 | `1c-meta-info` |
| `meta-remove` | 2510 | 33 | нет | 2 | 0 | `1c-meta-remove` |
| `meta-validate` | 1231 | 14 | нет | 2 | 0 | `1c-meta-validate` |
| `mxl-compile` | 9507 | 175 | нет | 2 | 0 | `1c-mxl-compile` |
| `mxl-decompile` | 2818 | 42 | нет | 2 | 0 | `1c-mxl-decompile` |
| `mxl-info` | 4961 | 89 | нет | 2 | 0 | `1c-mxl-info` |
| `mxl-validate` | 1203 | 13 | нет | 2 | 0 | `1c-mxl-validate` |
| `role-compile` | 4591 | 80 | нет | 2 | 0 | `1c-role-compile` |
| `role-info` | 1476 | 24 | нет | 2 | 0 | `1c-role-info` |
| `role-validate` | 1877 | 21 | нет | 2 | 0 | `1c-role-validate` |
| `skd-compile` | 16228 | 328 | нет | 2 | 0 | `1c-skd-compile` |
| `skd-decompile` | 3122 | 27 | нет | 2 | 0 | `1c-skd-decompile` |
| `skd-edit` | 15111 | 245 | нет | 2 | 0 | `1c-skd-edit` |
| `skd-info` | 3686 | 57 | нет | 2 | 0 | `1c-skd-info` |
| `skd-validate` | 1323 | 14 | нет | 2 | 0 | `1c-skd-validate` |
| `subsystem-compile` | 1781 | 36 | нет | 2 | 0 | `1c-subsystem-compile` |
| `subsystem-edit` | 2165 | 34 | нет | 2 | 0 | `1c-subsystem-edit` |
| `subsystem-info` | 2230 | 38 | нет | 2 | 0 | `1c-subsystem-info` |
| `subsystem-validate` | 1164 | 14 | нет | 2 | 0 | `1c-subsystem-validate` |
| `support-edit` | 2230 | 20 | нет | 2 | 0 | — |
| `template-add` | 4377 | 54 | нет | 2 | 0 | `1c-template-add` |
| `template-remove` | 1446 | 23 | нет | 2 | 0 | `1c-template-remove` |
| `web-info` | 2738 | 42 | нет | 2 | 0 | `1c-web-info` |
| `web-publish` | 4480 | 70 | нет | 2 | 0 | `1c-web-publish` |
| `web-stop` | 1346 | 28 | нет | 2 | 0 | `1c-web-stop` |
| `web-test` | 32629 | 478 | нет | 65 | 0 | `1c-web-test` |
| `web-unpublish` | 2039 | 34 | нет | 2 | 0 | `1c-web-unpublish` |
| `xdto-compile` | 4837 | 76 | нет | 2 | 0 | `1c-xdto-compile` |
| `xdto-decompile` | 2553 | 37 | нет | 2 | 0 | `1c-xdto-decompile` |
| `xdto-edit` | 4298 | 71 | нет | 2 | 0 | `1c-xdto-edit` |
| `xdto-info` | 3599 | 51 | нет | 2 | 0 | `1c-xdto-info` |
| `xdto-validate` | 1754 | 25 | нет | 2 | 0 | `1c-xdto-validate` |

## claude-code-skills-1c (116)

| Навык | Знаков | Строк тела | Справочник | Скриптов | Проверок | Пара |
|---|---|---|---|---|---|---|
| `1c-bsl-validate` | 4247 | 55 | нет | 2 | 0 | — |
| `1c-bsp-api` | 8990 | 114 | нет | 2 | 0 | — |
| `1c-bsp-command` | 7307 | 131 | нет | 0 | 1 | — |
| `1c-bsp-registration` | 7553 | 129 | нет | 0 | 1 | — |
| `1c-cf-add-object` | 1953 | 35 | нет | 0 | 1 | — |
| `1c-cf-edit` | 2356 | 35 | 3070 зн. | 2 | 1 | `cf-edit` |
| `1c-cf-info` | 1515 | 29 | нет | 2 | 1 | `cf-info` |
| `1c-cf-init` | 2690 | 48 | нет | 2 | 1 | `cf-init` |
| `1c-cf-new-project` | 2116 | 41 | нет | 0 | 1 | — |
| `1c-cf-validate` | 1241 | 14 | нет | 2 | 1 | `cf-validate` |
| `1c-cfe-borrow` | 4682 | 63 | нет | 2 | 1 | `cfe-borrow` |
| `1c-cfe-diff` | 1920 | 33 | нет | 2 | 1 | `cfe-diff` |
| `1c-cfe-full-cycle` | 2196 | 39 | нет | 0 | 1 | — |
| `1c-cfe-init` | 2585 | 43 | нет | 2 | 1 | `cfe-init` |
| `1c-cfe-patch-method` | 2995 | 50 | нет | 2 | 1 | `cfe-patch-method` |
| `1c-cfe-validate` | 1255 | 14 | нет | 2 | 1 | `cfe-validate` |
| `1c-config-index` | 6042 | 76 | нет | 2 | 0 | — |
| `1c-config-router` | 3660 | 89 | нет | 0 | 1 | — |
| `1c-db-create` | 2600 | 47 | нет | 2 | 1 | `db-create` |
| `1c-db-dump-cf` | 2862 | 50 | нет | 2 | 1 | `db-dump-cf` |
| `1c-db-dump-dt` | 3259 | 50 | нет | 2 | 1 | `db-dump-dt` |
| `1c-db-dump-xml` | 4432 | 66 | нет | 2 | 1 | `db-dump-xml` |
| `1c-db-list` | 4878 | 113 | нет | 0 | 1 | `db-list` |
| `1c-db-load-cf` | 2995 | 51 | нет | 2 | 1 | `db-load-cf` |
| `1c-db-load-dt` | 3880 | 56 | нет | 2 | 1 | `db-load-dt` |
| `1c-db-load-git` | 3393 | 52 | нет | 2 | 1 | `db-load-git` |
| `1c-db-load-xml` | 6588 | 109 | нет | 2 | 1 | `db-load-xml` |
| `1c-db-run` | 2829 | 48 | нет | 2 | 1 | `db-run` |
| `1c-db-update` | 3770 | 63 | нет | 2 | 1 | `db-update` |
| `1c-epf-add-form` | 2108 | 35 | нет | 2 | 1 | — |
| `1c-epf-build` | 3867 | 52 | нет | 4 | 1 | `epf-build` |
| `1c-epf-dump` | 3043 | 43 | нет | 2 | 1 | `epf-dump` |
| `1c-epf-full-cycle` | 2139 | 44 | нет | 0 | 1 | — |
| `1c-epf-scaffold` | 1141 | 20 | нет | 2 | 1 | — |
| `1c-epf-validate` | 1339 | 14 | нет | 2 | 1 | `epf-validate` |
| `1c-erf-build` | 3079 | 44 | нет | 0 | 1 | `erf-build` |
| `1c-erf-dump` | 3041 | 44 | нет | 0 | 1 | `erf-dump` |
| `1c-erf-init` | 1270 | 21 | нет | 2 | 1 | `erf-init` |
| `1c-erf-validate` | 1414 | 15 | нет | 0 | 1 | `erf-validate` |
| `1c-form-add` | 2925 | 42 | нет | 2 | 1 | `form-add` |
| `1c-form-compile` | 20276 | 400 | нет | 2 | 1 | `form-compile` |
| `1c-form-decompile` | 5189 | 60 | нет | 2 | 1 | `form-decompile` |
| `1c-form-edit` | 4733 | 101 | нет | 2 | 1 | `form-edit` |
| `1c-form-info` | 986 | 14 | нет | 2 | 1 | `form-info` |
| `1c-form-patterns` | 9394 | 196 | нет | 0 | 1 | `form-patterns` |
| `1c-form-remove` | 1344 | 23 | нет | 2 | 1 | `form-remove` |
| `1c-form-validate` | 3132 | 39 | нет | 2 | 1 | `form-validate` |
| `1c-help-manage` | 1684 | 21 | нет | 2 | 1 | — |
| `1c-interface-edit` | 2373 | 46 | 1740 зн. | 2 | 1 | `interface-edit` |
| `1c-interface-validate` | 1233 | 14 | нет | 2 | 1 | `interface-validate` |
| `1c-mcp-toolkit` | 20199 | 369 | нет | 3 | 0 | — |
| `1c-meta-compile` | 4670 | 85 | нет | 2 | 1 | `meta-compile` |
| `1c-meta-decompile` | 3066 | 26 | нет | 2 | 0 | `meta-decompile` |
| `1c-meta-edit` | 4441 | 71 | нет | 2 | 1 | `meta-edit` |
| `1c-meta-info` | 3422 | 54 | нет | 2 | 1 | `meta-info` |
| `1c-meta-remove` | 2494 | 33 | нет | 2 | 1 | `meta-remove` |
| `1c-meta-validate` | 3063 | 37 | нет | 2 | 1 | `meta-validate` |
| `1c-mxl-compile` | 2483 | 39 | нет | 2 | 1 | `mxl-compile` |
| `1c-mxl-decompile` | 1940 | 29 | нет | 2 | 1 | `mxl-decompile` |
| `1c-mxl-info` | 4958 | 89 | нет | 2 | 1 | `mxl-info` |
| `1c-mxl-validate` | 1173 | 13 | нет | 2 | 1 | `mxl-validate` |
| `1c-naparnik` | 12349 | 214 | нет | 0 | 0 | — |
| `1c-platform-docs` | 2919 | 57 | нет | 0 | 1 | — |
| `1c-query-optimization` | 2274 | 52 | нет | 0 | 1 | — |
| `1c-query-validate` | 4790 | 64 | нет | 2 | 0 | — |
| `1c-role-compile` | 3401 | 69 | нет | 2 | 1 | `role-compile` |
| `1c-role-info` | 1477 | 24 | нет | 2 | 1 | `role-info` |
| `1c-role-validate` | 2713 | 38 | нет | 2 | 1 | `role-validate` |
| `1c-skd-compile` | 13565 | 293 | нет | 2 | 1 | `skd-compile` |
| `1c-skd-decompile` | 5101 | 50 | нет | 2 | 1 | `skd-decompile` |
| `1c-skd-edit` | 10249 | 195 | нет | 2 | 1 | `skd-edit` |
| `1c-skd-info` | 3172 | 52 | нет | 2 | 1 | `skd-info` |
| `1c-skd-validate` | 2489 | 30 | нет | 2 | 1 | `skd-validate` |
| `1c-ssl-patterns` | 3499 | 51 | нет | 0 | 1 | — |
| `1c-subsystem-compile` | 1806 | 36 | нет | 2 | 1 | `subsystem-compile` |
| `1c-subsystem-edit` | 2173 | 34 | нет | 2 | 1 | `subsystem-edit` |
| `1c-subsystem-info` | 2236 | 38 | нет | 2 | 1 | `subsystem-info` |
| `1c-subsystem-validate` | 2199 | 28 | нет | 2 | 1 | `subsystem-validate` |
| `1c-support-state` | 4734 | 54 | нет | 2 | 1 | — |
| `1c-template-add` | 4369 | 54 | нет | 2 | 1 | `template-add` |
| `1c-template-remove` | 1453 | 23 | нет | 2 | 1 | `template-remove` |
| `1c-vanessa-steps` | 4955 | 66 | нет | 5 | 0 | — |
| `1c-web-info` | 1481 | 36 | нет | 2 | 0 | `web-info` |
| `1c-web-publish` | 4263 | 67 | нет | 2 | 0 | `web-publish` |
| `1c-web-stop` | 1340 | 28 | нет | 2 | 0 | `web-stop` |
| `1c-web-test` | 21635 | 401 | нет | 5 | 0 | `web-test` |
| `1c-web-unpublish` | 2050 | 34 | нет | 2 | 0 | `web-unpublish` |
| `1c-xdto-compile` | 4840 | 76 | нет | 2 | 0 | `xdto-compile` |
| `1c-xdto-decompile` | 2556 | 37 | нет | 2 | 0 | `xdto-decompile` |
| `1c-xdto-edit` | 4304 | 71 | нет | 2 | 0 | `xdto-edit` |
| `1c-xdto-info` | 3602 | 51 | нет | 2 | 0 | `xdto-info` |
| `1c-xdto-validate` | 1757 | 25 | нет | 2 | 0 | `xdto-validate` |
| `1c77-dev` | 6873 | 67 | нет | 5 | 0 | — |
| `ai-edt-tools` | 11167 | 131 | нет | 0 | 1 | — |
| `claude-env-setup` | 6419 | 81 | нет | 0 | 0 | — |
| `claude-md-bootstrap` | 7027 | 99 | нет | 0 | 0 | — |
| `cleverence-mslx` | 12989 | 159 | нет | 1 | 0 | — |
| `composing-1c-queries` | 21752 | 425 | нет | 0 | 1 | — |
| `docx-from-sample` | 8141 | 122 | нет | 4 | 0 | — |
| `humanize-ai-text` | 17534 | 205 | нет | 1 | 0 | — |
| `img-grid-analysis` | 2673 | 47 | нет | 1 | 1 | — |
| `kd2-rules` | 9383 | 162 | нет | 0 | 0 | — |
| `kd31-rules` | 7908 | 92 | нет | 2 | 0 | — |
| `lmstudio-api` | 14931 | 215 | нет | 0 | 0 | — |
| `md-to-docx` | 3270 | 51 | нет | 1 | 0 | — |
| `meeting-to-tasks` | 7713 | 106 | нет | 0 | 0 | — |
| `mermaid-diagrams` | 6564 | 204 | нет | 0 | 1 | — |
| `mermaid-render` | 3925 | 54 | нет | 1 | 0 | — |
| `powershell-windows` | 3057 | 83 | нет | 0 | 1 | — |
| `prompt-enhancer` | 8573 | 87 | нет | 0 | 0 | — |
| `skill-creator` | 32189 | 318 | нет | 10 | 0 | — |
| `sync-fork` | 3158 | 45 | нет | 0 | 0 | — |
| `transcribe` | 22228 | 183 | нет | 13 | 0 | — |
| `transcribe-audio-local` | 5193 | 80 | нет | 4 | 0 | — |
| `v8unpack-cf` | 5200 | 104 | нет | 0 | 1 | — |
| `zup-hr-api-reference` | 2483 | 30 | нет | 0 | 0 | — |

