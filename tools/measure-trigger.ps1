# Меряет частоту срабатывания навыка developing-1c-configurations в обеих
# средах, ДО и ПОСЛЕ правки поля description. Мера — только поле Навык.
#
# Прогон Claude Code занимает ~7 минут, а инструмент запуска команд обрывается
# на 600 секундах: 24 прогона (6 формулировок × 2 среды × 2 среза) подряд
# синхронно не выполнить. Поэтому весь конвейер — снять «до», переписать
# description, переустановить навыки, снять «после», записать итог —
# собран в одном скрипте и рассчитан на единственный запуск в фоне; вызывающая
# сторона потом читает файл прогресса и итоговый файл-свидетельство, не сам
# скрипт.
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

param(
  [string]$EvidenceFile = (Join-Path $PSScriptRoot '..\docs\evidence\2026-08-22-trigger-rate.md'),
  [string]$SkillFile    = (Join-Path $PSScriptRoot '..\skills\developing-1c-configurations\SKILL.md'),
  [string]$ProgressFile = (Join-Path $env:TEMP 'trigger-measure-progress.jsonl'),
  [switch]$DryRun
)

$NewDescription = 'Разработка конфигураций 1С:Предприятие 8.3 по исходникам — от планирования доработки до кода. Применяется, когда ответ должен соответствовать стандартам 1С и соглашениям типовых конфигураций, а не общему знанию языка: справочник, документ, регистр, форма, запрос, отчёт, обработка, роль, расширение, БСП, СКД, файлы .bsl, .epf, .cf.'

$prompts = @(
  'Напиши запрос по остаткам номенклатуры на складе.',
  'Напиши запрос 1С по остаткам номенклатуры.',
  'Сделай отчёт по продажам за месяц.',
  'Добавь справочник Договоры.',
  'Поправь проведение документа Реализация.',
  'Сделай печатную форму счёта.'
)
$envs = @('kilo', 'claude')
$run = Join-Path $PSScriptRoot 'run-prompt.ps1'
$install = Join-Path $PSScriptRoot 'install-skills.ps1'

if (Test-Path $ProgressFile) { Remove-Item $ProgressFile -Force }
function Log-Progress($obj) {
  ($obj | ConvertTo-Json -Compress) | Add-Content -Path $ProgressFile -Encoding UTF8
}
Log-Progress @{ event = 'start'; dryRun = [bool]$DryRun; time = (Get-Date).ToString('s') }

function Run-Stage([string]$label) {
  $rows = @()
  foreach ($p in $prompts) {
    foreach ($e in $envs) {
      if ($DryRun) {
        $navyk = (Get-Random -Minimum 0 -Maximum 2) -eq 1
        $log = '(dry-run, без прогона)'
      } else {
        $r = & $run -Env $e -Prompt $p
        $navyk = [bool]$r.Навык
        $log = $r.Журнал
      }
      $rows += [pscustomobject]@{
        Этап   = $label
        Среда  = $e
        Задача = $p
        Навык  = $navyk
        Журнал = $log
      }
      Log-Progress @{ event = 'run'; stage = $label; env = $e; prompt = $p; navyk = $navyk; time = (Get-Date).ToString('s') }
    }
  }
  return $rows
}

$before = Run-Stage 'до'
Log-Progress @{ event = 'stage-done'; stage = 'до'; time = (Get-Date).ToString('s') }

# --- правка description ---
$oldText = Get-Content $SkillFile -Raw -Encoding UTF8
$oldDescMatch = [regex]::Match($oldText, '(?m)^description:\s*(.+)$')
$oldDesc = $oldDescMatch.Groups[1].Value

if (-not $DryRun) {
  $newText = $oldText -replace '(?m)^description:.*$', ("description: " + $NewDescription)
  [System.IO.File]::WriteAllText($SkillFile, $newText, (New-Object System.Text.UTF8Encoding($false)))
  Log-Progress @{ event = 'desc-changed'; oldLen = $oldDesc.Length; newLen = $NewDescription.Length; time = (Get-Date).ToString('s') }

  # --- переустановка навыков в обе среды ---
  $installOut = & powershell -NoProfile -File $install
  Log-Progress @{ event = 'install'; output = ($installOut -join ' | '); time = (Get-Date).ToString('s') }
} else {
  Log-Progress @{ event = 'desc-changed-skipped-dryrun'; time = (Get-Date).ToString('s') }
}

$after = Run-Stage 'после'
Log-Progress @{ event = 'stage-done'; stage = 'после'; time = (Get-Date).ToString('s') }

# --- построение итоговых таблиц ---
function Table($rows) {
  $lines = @('| Среда | Задача | Навык |', '|---|---|---|')
  foreach ($r in $rows) {
    $lines += ('| {0} | {1} | {2} |' -f $r.Среда, $r.Задача, $r.Навык)
  }
  return ($lines -join "`n")
}

$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine('# Частота срабатывания навыка `developing-1c-configurations`')
[void]$sb.AppendLine()
[void]$sb.AppendLine('Мера — поле `Навык` (структурный `tool_use` с именем `Skill` у Claude Code,')
[void]$sb.AppendLine('баннер вызова в журнале у Kilo). Поле `Вопросов` из `run-prompt.ps1` в замер')
[void]$sb.AppendLine('не включено: оно дважды дало ложные срабатывания — считало тернарный оператор')
[void]$sb.AppendLine('1С `?(Условие, Если, Иначе)` внутри сгенерированного кода и объявление')
[void]$sb.AppendLine('`<?xml version...?>` как вопросы.')
[void]$sb.AppendLine()
[void]$sb.AppendLine('Старая формулировка `description` (перечень тем):')
[void]$sb.AppendLine()
[void]$sb.AppendLine('```')
[void]$sb.AppendLine($oldDesc)
[void]$sb.AppendLine('```')
[void]$sb.AppendLine()
[void]$sb.AppendLine('Новая формулировка (последствие для ответа, а не тема):')
[void]$sb.AppendLine()
[void]$sb.AppendLine('```')
[void]$sb.AppendLine($NewDescription)
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
  $bc = @($b | Where-Object Навык).Count
  $ac = @($a | Where-Object Навык).Count
  [void]$sb.AppendLine("**${ename}: было $bc из $($b.Count), стало $ac из $($a.Count).**")
  [void]$sb.AppendLine()
}

[System.IO.File]::WriteAllText($EvidenceFile, $sb.ToString(), (New-Object System.Text.UTF8Encoding($false)))
Log-Progress @{ event = 'done'; time = (Get-Date).ToString('s') }
"ЗАМЕР ЗАВЕРШЁН" | Add-Content -Path $ProgressFile -Encoding UTF8
