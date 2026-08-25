# Меряет частоту срабатывания навыка developing-1c-configurations в обеих
# средах, ДО и ПОСЛЕ правки поля description. Мера — только поле Навык.
#
# Н-12 (docs/reviews/2026-08-23-core-review.md): раньше все формулировки были
# из предметной области набора — прибор мерил только полноту (сколько поднял
# там, где надо) и структурно не мог наказать переразросшееся описание: любое
# расширение оценивалось не хуже нейтрального. Теперь у каждой формулировки
# есть Ожидание (должен навык подняться или нет), в наборе есть формулировки
# из ЧУЖИХ областей (другой язык, другая СУБД, другой веб-сервер), и итог —
# ДВЕ величины на среду и срез: сколько поднял там, где надо (полнота), и
# сколько поднял там, где не надо (ложные срабатывания). Отрицательные
# формулировки — близкие, но однозначные промашки (обзор рецензента отсеял
# двусмысленные кандидаты вроде «перенеси базу 1С на PostgreSQL»: это
# законная область 1c-build-and-db, а не «не должен подняться»).
#
# Реалистичный размер набора — рекомендация того же ревью: 6 положительных +
# 5 отрицательных, без слепых троекратных повторов (повтор оправдан только
# для формулировки, разошедшейся между срезами, — здесь такого нет, повторов
# нет). Полная сетка 11 формулировок × 2 среды × 2 среза = 44 прогона; при
# ~7 минутах на прогон Claude Code это часы фонового времени. Задача 5 не
# требует гонять эту полную сетку заново ради этой находки — требуется
# показать, что прибор ТЕПЕРЬ СПОСОБЕН наказывать. Это показано отдельно,
# живым прогоном малой выборки (не этим скриптом): tools/run-prompt.ps1
# -Env kilo и -Env claude на двух отрицательных формулировках против уже
# установленного (расширенного) описания дали Навык=False на обеих в обеих
# средах — 0 ложных срабатываний на выборке, задокументировано в
# docs/evidence/2026-08-23-task5-instrument-fixes.md. Полный прогон этого
# скрипта остаётся доступен (см. ниже), но не запускался повторно в рамках
# задачи 5 — прибор при этом уже умеет считать вторую величину, что и
# требовалось.
#
# Прогон Claude Code занимает ~7 минут, а инструмент запуска команд обрывается
# на 600 секундах: полную сетку подряд синхронно не выполнить. Поэтому весь
# конвейер — снять «до», переписать description, переустановить навыки, снять
# «после», записать итог — собран в одном скрипте и рассчитан на единственный
# запуск в фоне; вызывающая сторона потом читает файл прогресса и итоговый
# файл-свидетельство, не сам скрипт.
#
# М-18: раньше скрипт не ставил навыки перед стадией «до» — она измеряла то,
# что было установлено РАНЬШЕ (возможно, стале от прошлого прогона), а
# $oldDesc для отчёта читался из репозитория уже ПОСЛЕ стадии «до»: отчёт мог
# называть не ту формулировку, которая реально измерялась. Теперь навыки
# ставятся и перед стадией «до» тоже, $oldDesc читается сразу после установки,
# и хэш обеих формулировок (до/после) пишется в файл прогресса — по нему
# видно, что именно было установлено в момент каждого среза.
#
# Поле Навык у Kilo — с задачи 5 структурный признак (tools/run-prompt.ps1:
# kilo.exe run --format json, событие tool_use с part.tool == "skill"), а не
# подстрочный поиск имени по журналу — М-17/М-18 называли старый подстрочный
# поиск источником ложных срабатываний. У Claude Code это по-прежнему
# структурный tool_use "Skill" в stream-json. Оба прибора теперь одного
# класса: числа Kilo и Claude Code сравнимы напрямую, «верхней оценкой» Kilo
# больше не является.
#
# Поле Вопросов, которое возвращает run-prompt.ps1, в замер не идёт: оно дважды
# дало ложные срабатывания (тернарный оператор 1С ?(Условие, Если, Иначе)
# внутри сгенерированного кода и объявление <?xml version...?>). Чем больше
# кода написал агент, тем «навязчивее» он выглядел бы по этому полю — оно не
# о том, поднялся ли навык.
#
# Наблюдение с прогона 2026-08-22: даже фоновый процесс здесь может быть
# принудительно остановлен инфраструктурой раньше, чем скрипт дойдёт до
# конца (в одном случае — примерно на 69-й минуте, ещё на стадии «после»).
# Прогресс при этом не теряется: каждая строка (включая desc-changed и
# install) дописывается в $ProgressFile сразу после события, а не только в
# конце. Если скрипт оборвался, не дойдя до строки «ЗАМЕР ЗАВЕРШЁН» —
# правка description и переустановка навыков (если в файле прогресса уже
# есть событие desc-changed) уже применены, откатывать их не нужно; остаётся
# доснять через run-prompt.ps1 только те пары (среда, задача) стадии
# «после», которых не хватает в файле прогресса, по одной задаче за вызов —
# передача нескольких формулировок одним вызовом через границу
# Bash → PowerShell склеивается в одну строку по запятой и портит данные.

# C-1: текста описания в этом скрипте больше нет ни в каком виде. Раньше здесь
# стояла константа $NewDescription, и строка «правка description» безусловно
# писала её в SKILL.md. Константа разошлась с поставляемым описанием (в наборе
# тире, в константе двоеточие) и при первом же штатном прогоне вернула бы в
# набор фронтматтер, который не разбирается YAML: ровно та Н-01, ради которой
# заведён tools/check-manifests.py. Заодно срез «после» мерил бы формулировку,
# которой в наборе нет, — и хэши М-18 не с чем было бы сверять.
#
# Теперь «после»-формулировка приходит снаружи: -NewDescription '<текст>' либо
# -NewDescriptionFile <путь>. Расходиться нечему — расходиться больше не с чем.
#
# Правило набора, заведённое этой же находкой: ЛЮБОЙ инструмент, который пишет
# в skills/, обязан заканчиваться прогоном tools/check-manifests.py и падать
# при ненулевом коде. Здесь это Set-SkillDescription: пишет, проверяет, при
# ненуле возвращает файл в исходное состояние и роняет прогон.
param(
  [string]$EvidenceFile = (Join-Path $PSScriptRoot '..\docs\evidence\2026-08-22-trigger-rate.md'),
  [string]$SkillFile    = (Join-Path $PSScriptRoot '..\skills\developing-1c-configurations\SKILL.md'),
  [string]$ProgressFile = (Join-Path $env:TEMP 'trigger-measure-progress.jsonl'),
  [string]$NewDescription = '',
  [string]$NewDescriptionFile = '',
  # Записать «после»-формулировку в SKILL.md, проверить манифесты и выйти —
  # без прогонов агентов. Нужен, чтобы саму запись можно было проверить
  # отдельно от многочасового замера.
  [switch]$ApplyDescriptionOnly,
  [switch]$DryRun
)

# Обёртка читает вывод сторонних программ: скриптов набора на Python
# и агентских CLI. PowerShell 5.1 декодирует stdout нативной программы
# по [Console]::OutputEncoding, а он по умолчанию равен кодовой странице
# консоли (cp866 на русской Windows). Скрипты набора с 25.08.2026 печатают
# UTF-8 всегда, поэтому без этой строки кириллица приходит кракозябрами —
# и не просто на экран: run-acceptance кладёт этот текст в progress.jsonl
# и в сообщение throw, то есть мусор замерзает в свидетельстве приёмки.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$CheckManifests = Join-Path $RepoRoot 'tools\check-manifests.py'

# Ожидание = $true: навык обязан подняться (область набора).
# Ожидание = $false: навык подниматься не должен (чужая область — другой
# язык, другая СУБД, другой веб-сервер). Отбор со сверкой по возражениям
# рецензента (Н-12): не «перенеси базу 1С на PostgreSQL» (это /DumpIB +
# /RestoreIB — законная область 1c-build-and-db), не «T-SQL к базе 1С
# напрямую» (ровно та задача, ради которой описание и расширено), не
# «разбери лог Apache» (не-очевидная промашка) — только однозначно чужое.
$prompts = @(
  [pscustomobject]@{ Text = 'Напиши запрос по остаткам номенклатуры на складе.'; Expect = $true }
  [pscustomobject]@{ Text = 'Напиши запрос 1С по остаткам номенклатуры.'; Expect = $true }
  [pscustomobject]@{ Text = 'Сделай отчёт по продажам за месяц.'; Expect = $true }
  [pscustomobject]@{ Text = 'Добавь справочник Договоры.'; Expect = $true }
  [pscustomobject]@{ Text = 'Поправь проведение документа Реализация.'; Expect = $true }
  [pscustomobject]@{ Text = 'Сделай печатную форму счёта.'; Expect = $true }
  [pscustomobject]@{ Text = 'Напиши SQL-запрос к MS SQL по таблице заказов.'; Expect = $false }
  [pscustomobject]@{ Text = 'Настрой резервное копирование PostgreSQL по расписанию.'; Expect = $false }
  [pscustomobject]@{ Text = 'Объясни синтаксис цикла for в Python.'; Expect = $false }
  [pscustomobject]@{ Text = 'Напиши функцию сортировки массива на JavaScript.'; Expect = $false }
  [pscustomobject]@{ Text = 'Как настроить проксирование запросов в nginx?'; Expect = $false }
)
$envs = @('kilo', 'claude')
$run = Join-Path $PSScriptRoot 'run-prompt.ps1'
$install = Join-Path $PSScriptRoot 'install-skills.ps1'

if (Test-Path $ProgressFile) { Remove-Item $ProgressFile -Force }
function Log-Progress($obj) {
  ($obj | ConvertTo-Json -Compress) | Add-Content -Path $ProgressFile -Encoding UTF8
}
Log-Progress @{ event = 'start'; dryRun = [bool]$DryRun; time = (Get-Date).ToString('s') }

function Get-DescHash([string]$text) {
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($text)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  -join ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') })
}

function Resolve-NewDescription {
  if ($NewDescriptionFile) {
    if (-not (Test-Path $NewDescriptionFile)) {
      throw "файл с «после»-формулировкой не найден: $NewDescriptionFile"
    }
    return ([System.IO.File]::ReadAllText($NewDescriptionFile, [System.Text.Encoding]::UTF8)).Trim()
  }
  if ($NewDescription) { return $NewDescription.Trim() }
  throw @'
не задана «после»-формулировка description. Замер «переписать и померить»
берёт её только снаружи: -NewDescription '<текст>' либо -NewDescriptionFile
<путь>. Константы с текстом описания в скрипте нет намеренно (C-1): она
разошлась с поставляемым SKILL.md и возвращала в набор двоеточие, ломающее
YAML-фронтматтер.
'@
}

# Пишет description в SKILL.md и тут же проверяет манифесты. Ненулевой код —
# файл возвращается в исходное состояние, прогон падает. check-skills.py на
# такую порчу не годится: он разбирает фронтматтер регуляркой и молча проходит
# мимо двоеточия (проверено: на испорченном файле он вернул 0, а
# check-manifests.py — 1).
function Set-SkillDescription([string]$path, [string]$desc) {
  $before = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
  # $ в тексте описания экранируется: в -replace он значил бы ссылку на группу.
  # Замена литеральная (String.Replace), поэтому пара — ровно '$$': её -replace
  # и схлопнет в один $. Четыре давали два — инструмент писал в skills/ не то,
  # что померил, и хэш «после» считался бы с неисправленной строки.
  $safe = $desc.Replace('$', '$$')
  # [^\r\n]* вместо .* : в многострочном режиме .NET «.» съедает \r перед \n,
  # и запись молча превращала CRLF этой строки в LF. Инструмент, пишущий
  # в skills/, не имеет права менять в файле ничего, кроме самого описания.
  $updated = $before -replace '(?m)^description:[^\r\n]*', ("description: " + $safe)
  [System.IO.File]::WriteAllText($path, $updated, (New-Object System.Text.UTF8Encoding($false)))

  # PowerShell 5.1 оборачивает stderr нативной программы в ErrorRecord при
  # перенаправлении; при $ErrorActionPreference = 'Stop' у вызывающей стороны
  # это роняет прогон раньше, чем мы посмотрим на код возврата.
  $prev = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    $out = (& python $CheckManifests 2>&1 | Out-String).Trim()
    $code = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $prev
  }
  Log-Progress @{ event = 'check-manifests'; exit = $code; output = $out; time = (Get-Date).ToString('s') }
  if ($code -ne 0) {
    [System.IO.File]::WriteAllText($path, $before, (New-Object System.Text.UTF8Encoding($false)))
    throw ("запись description отвергнута tools/check-manifests.py (код $code), файл возвращён в исходное состояние:`n" + $out)
  }
  return $out
}

# Формулировку разрешаем ДО стадии «до»: иначе о пропущенном параметре скрипт
# узнал бы через час прогонов.
$newDesc = Resolve-NewDescription

if ($ApplyDescriptionOnly) {
  $checkOut = Set-SkillDescription $SkillFile $newDesc
  Log-Progress @{ event = 'apply-only'; hash = (Get-DescHash $newDesc); len = $newDesc.Length; time = (Get-Date).ToString('s') }
  $checkOut
  "description записан в $SkillFile и принят check-manifests.py (код 0)"
  return
}

function Run-Stage([string]$label) {
  $rows = @()
  foreach ($p in $prompts) {
    foreach ($e in $envs) {
      if ($DryRun) {
        $navyk = (Get-Random -Minimum 0 -Maximum 2) -eq 1
        $log = '(dry-run, без прогона)'
      } else {
        $r = & $run -Env $e -Prompt $p.Text
        $navyk = [bool]$r.Навык
        $log = $r.Журнал
      }
      $rows += [pscustomobject]@{
        Этап     = $label
        Среда    = $e
        Задача   = $p.Text
        Ожидание = $p.Expect
        Навык    = $navyk
        Верно    = ($navyk -eq $p.Expect)
        Журнал   = $log
      }
      Log-Progress @{ event = 'run'; stage = $label; env = $e; prompt = $p.Text; expect = $p.Expect; navyk = $navyk; time = (Get-Date).ToString('s') }
    }
  }
  return $rows
}

# --- М-18: ставим навыки ДО стадии «до», не только перед «после» ---
if (-not $DryRun) {
  $installOutBefore = & powershell -NoProfile -File $install
  Log-Progress @{ event = 'install-before'; output = ($installOutBefore -join ' | '); time = (Get-Date).ToString('s') }
} else {
  Log-Progress @{ event = 'install-before-skipped-dryrun'; time = (Get-Date).ToString('s') }
}

$oldText = Get-Content $SkillFile -Raw -Encoding UTF8
$oldDescMatch = [regex]::Match($oldText, '(?m)^description:\s*(.+)$')
$oldDesc = $oldDescMatch.Groups[1].Value
Log-Progress @{ event = 'before-hash'; hash = (Get-DescHash $oldDesc); len = $oldDesc.Length; time = (Get-Date).ToString('s') }

$before = Run-Stage 'до'
Log-Progress @{ event = 'stage-done'; stage = 'до'; time = (Get-Date).ToString('s') }

# --- правка description ---
if (-not $DryRun) {
  Set-SkillDescription $SkillFile $newDesc | Out-Null
  Log-Progress @{ event = 'desc-changed'; oldLen = $oldDesc.Length; newLen = $newDesc.Length; time = (Get-Date).ToString('s') }

  # --- переустановка навыков в обе среды ---
  $installOut = & powershell -NoProfile -File $install
  Log-Progress @{ event = 'install'; output = ($installOut -join ' | '); time = (Get-Date).ToString('s') }
  Log-Progress @{ event = 'after-hash'; hash = (Get-DescHash $newDesc); len = $newDesc.Length; time = (Get-Date).ToString('s') }
} else {
  Log-Progress @{ event = 'desc-changed-skipped-dryrun'; time = (Get-Date).ToString('s') }
}

$after = Run-Stage 'после'
Log-Progress @{ event = 'stage-done'; stage = 'после'; time = (Get-Date).ToString('s') }

# --- построение итоговых таблиц ---
function Table($rows) {
  $lines = @('| Среда | Задача | Ожидание | Навык | Верно |', '|---|---|---|---|---|')
  foreach ($r in $rows) {
    $exp = if ($r.Ожидание) { 'да' } else { 'нет' }
    $ok = if ($r.Верно) { 'да' } else { 'НЕТ' }
    $lines += ('| {0} | {1} | {2} | {3} | {4} |' -f $r.Среда, $r.Задача, $exp, $r.Навык, $ok)
  }
  return ($lines -join "`n")
}

$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine('# Частота срабатывания навыка `developing-1c-configurations`')
[void]$sb.AppendLine()
[void]$sb.AppendLine('Мера — поле `Навык`: структурный `tool_use` с именем `Skill` у Claude Code')
[void]$sb.AppendLine('(stream-json), структурный `tool_use` с `part.tool == "skill"` у Kilo')
[void]$sb.AppendLine('(`kilo.exe run --format json`, задача 5 — раньше был подстрочный поиск имени')
[void]$sb.AppendLine('по всему журналу, засчитывавший любое упоминание; прибор сам был назван')
[void]$sb.AppendLine('негодным, см. docs/reviews/2026-08-23-core-review.md, М-17/М-18). Оба прибора')
[void]$sb.AppendLine('теперь одного класса — числа сред сравнимы напрямую.')
[void]$sb.AppendLine()
[void]$sb.AppendLine('Каждая формулировка несёт **Ожидание**: должен ли навык подняться. Итог —')
[void]$sb.AppendLine('две величины на среду и срез: полнота (сколько поднял там, где надо) и')
[void]$sb.AppendLine('ложные срабатывания (сколько поднял там, где не надо). До задачи 5 прибор')
[void]$sb.AppendLine('второй величины не имел вовсе — все формулировки были из предметной области')
[void]$sb.AppendLine('набора, и любое расширение description оценивалось не хуже нейтрального')
[void]$sb.AppendLine('(Н-12).')
[void]$sb.AppendLine()
[void]$sb.AppendLine('Поле `Вопросов`, которое тоже возвращает `tools/run-prompt.ps1`, в этот замер')
[void]$sb.AppendLine('не включено:')
[void]$sb.AppendLine('оно дважды дало ложные срабатывания — считало вопросом тернарный оператор')
[void]$sb.AppendLine('1С `?(Условие, Если, Иначе)` внутри сгенерированного кода и объявление')
[void]$sb.AppendLine('`<?xml version...?>`. Чем больше кода писал агент, тем «назойливее» он')
[void]$sb.AppendLine('выглядел бы по этому полю — оно не о том, поднялся ли навык.')
[void]$sb.AppendLine()
[void]$sb.AppendLine('## Правка')
[void]$sb.AppendLine()
[void]$sb.AppendLine('Старая формулировка description:')
[void]$sb.AppendLine()
[void]$sb.AppendLine('```')
[void]$sb.AppendLine($oldDesc)
[void]$sb.AppendLine('```')
[void]$sb.AppendLine()
[void]$sb.AppendLine('Новая формулировка (последствие для ответа, а не тема):')
[void]$sb.AppendLine()
[void]$sb.AppendLine('```')
[void]$sb.AppendLine($newDesc)
[void]$sb.AppendLine('```')
[void]$sb.AppendLine()

foreach ($e in $envs) {
  $ename = if ($e -eq 'kilo') { 'Kilo' } else { 'Claude Code' }
  [void]$sb.AppendLine("## $ename -- до правки")
  [void]$sb.AppendLine()
  [void]$sb.AppendLine((Table (@($before | Where-Object { $_.Среда -eq $e }))))
  [void]$sb.AppendLine()
  [void]$sb.AppendLine("## $ename -- после правки")
  [void]$sb.AppendLine()
  [void]$sb.AppendLine((Table (@($after | Where-Object { $_.Среда -eq $e }))))
  [void]$sb.AppendLine()
}

[void]$sb.AppendLine('## Итог')
[void]$sb.AppendLine()
foreach ($e in $envs) {
  $ename = if ($e -eq 'kilo') { 'Kilo' } else { 'Claude Code' }
  $b = @($before | Where-Object { $_.Среда -eq $e })
  $a = @($after | Where-Object { $_.Среда -eq $e })
  $bPos = @($b | Where-Object Ожидание); $bNeg = @($b | Where-Object { -not $_.Ожидание })
  $aPos = @($a | Where-Object Ожидание); $aNeg = @($a | Where-Object { -not $_.Ожидание })
  $bHit = @($bPos | Where-Object Навык).Count
  $aHit = @($aPos | Where-Object Навык).Count
  $bFP  = @($bNeg | Where-Object Навык).Count
  $aFP  = @($aNeg | Where-Object Навык).Count
  [void]$sb.AppendLine("**${ename}: срабатывание на своей области — было $bHit из $($bPos.Count), стало $aHit из $($aPos.Count). Ложные срабатывания на чужой области — было $bFP из $($bNeg.Count), стало $aFP из $($aNeg.Count).**")
  [void]$sb.AppendLine()
}

[System.IO.File]::WriteAllText($EvidenceFile, $sb.ToString(), (New-Object System.Text.UTF8Encoding($false)))
Log-Progress @{ event = 'done'; time = (Get-Date).ToString('s') }
"ЗАМЕР ЗАВЕРШЁН" | Add-Content -Path $ProgressFile -Encoding UTF8
