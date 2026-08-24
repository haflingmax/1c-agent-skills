# Гоняет одну задачу в одной среде и сообщает, поднялся ли навык и сколько задано вопросов.
param(
  [ValidateSet('kilo','claude','codex')][string]$Env = 'kilo',
  [Parameter(Mandatory)][string]$Prompt,
  [string]$Dir
)
if (-not $Dir) { $Dir = Join-Path $env:TEMP ("1c-run\" + [guid]::NewGuid().ToString('N').Substring(0,8)) }
New-Item -ItemType Directory -Force $Dir | Out-Null
$log = Join-Path $Dir 'run.log'
switch ($Env) {
  'kilo' {
    # М-17/М-18: --format json даёт структурный журнал (raw JSON events),
    # тот же класс сигнала, что stream-json у Claude — проверено запуском
    # 2026-08-23, событие {"type":"tool_use",...,"part":{"tool":"skill",
    # "state":{"input":{"name":"developing-1c-configurations"}}}}.
    # Путь был зашит вместе с версией расширения (7.4.22) — и сломался молча,
    # когда обновление Kilo оборвалось: каталог расширения остался, а bin\kilo.exe
    # из него исчез (уцелел только внутри .incomplete-пакета установщика).
    # Прогоны при этом записывались как выполненные с «навык не сработал» —
    # неотличимо от честного отказа навыка выбраться. Проверено запуском
    # 24.08.2026: шесть прогонов приёмки дали пустые каталоги и вердикт False.
    #
    # Поэтому версия больше не зашита, а отсутствие исполняемого файла —
    # громкий отказ, а не тихий ноль. Чужой инструмент мы не судим (правило 11),
    # но и невыполненное за его прогон не выдаём.
    $exe = Get-ChildItem "$env:USERPROFILE\.vscode\extensions" -Filter 'kilocode.kilo-code-*' -Directory -ErrorAction SilentlyContinue |
      Sort-Object Name -Descending |
      ForEach-Object { Join-Path $_.FullName 'bin\kilo.exe' } |
      Where-Object { Test-Path $_ } |
      Select-Object -First 1
    if (-not $exe) {
      throw ("среда kilo недоступна: ни в одном каталоге " +
             "$env:USERPROFILE\.vscode\extensions\kilocode.kilo-code-* нет bin\kilo.exe. " +
             "Прогон не выполнялся — это не отказ навыка, а отсутствие среды.")
    }
    & $exe run --auto --dir $Dir --format json $Prompt *> $log
  }
  'claude' {
    # stream-json + verbose: обычный текстовый вывод не показывает вызов инструментов,
    # а Навык нужно ловить по факту, а не по прозе ответа. Вызывающая сторона обязана
    # давать этому процессу не меньше 900 секунд — claude -p с навыком внутри бегает
    # дольше, чем короткий запрос без инструментов, и обрывать его по короткому
    # таймауту значит мерить оборванные прогоны, а не реальные.
    Push-Location $Dir
    try { claude -p $Prompt --output-format stream-json --verbose *> $log } finally { Pop-Location }
  }
  'codex' {
    Push-Location $Dir
    try { codex exec --profile tpm --skip-git-repo-check $Prompt *> $log } finally { Pop-Location }
  }
}
$txt = if (Test-Path $log) { Get-Content $log -Raw -Encoding Unicode } else { '' }

# Пустой журнал — это НЕ «навык не сработал», это «прогон не состоялся».
# Дважды за один день приёмка выдала второе за первое: сперва на Kilo без
# исполняемого файла, потом на Codex, где все шесть журналов оказались
# нулевого размера. В обоих случаях вердикт был «выполнено, навык False» —
# неотличимо от честного отказа навыка выбраться, и оба раза он молча
# засчитывался как результат по набору.
#
# Отказ здесь громкий намеренно: лучше оборвать приёмку, чем принести
# цифру, за которой ничего нет.
if ([string]::IsNullOrWhiteSpace($txt)) {
  throw ("прогон в среде '$Env' не дал никакого вывода: $log пуст. " +
         "Это отсутствие прогона, а не отказ навыка. " +
         "Проверить доступность среды прежде, чем толковать результат.")
}

# Перечень имён навыков берётся из самого набора, а НЕ зашивается списком.
# Был зашит: '(developing-1c-configurations|1c-build-and-db)'. Как только
# появился третий навык (1c-queries), приёмка стала выдавать «навык не
# сработал» на прогонах, где он фактически вызывался, — проверено запуском
# 24.08.2026: в журнале Kilo лежит событие tool_use с
# part.state.input.name == "1c-queries", а вердикт был False.
#
# Дефект тихий и системный: он повторится на каждом из двенадцати оставшихся
# разделов, и каждый раз будет выглядеть как «раздел не выбирается»,
# то есть как дефект набора, а не прибора.
$skillNames = Get-ChildItem (Join-Path $PSScriptRoot '..\skills') -Directory |
  ForEach-Object { $_.Name }
if (-not $skillNames) { throw "не найдено ни одного навыка в skills/ — мерить нечем" }
$skillAlt = ($skillNames | ForEach-Object { [regex]::Escape($_) }) -join '|'
$skillPattern = "(^|:)($skillAlt)$"      # имя голое либо с префиксом плагина
$skillSubstr  = "($skillAlt)"            # для сред без структурного журнала
if ($Env -eq 'claude') {
  # Текстовый регэксп тут не работает: claude -p в stream-json не печатает баннер
  # вызова навыка прозой, вызов виден только как структурный tool_use-элемент JSONL.
  $navyk = $false
  $questions = 0
  foreach ($line in ($txt -split "`r?`n")) {
    $line = $line.Trim()
    if (-not $line) { continue }
    try { $evt = $line | ConvertFrom-Json -ErrorAction Stop } catch { continue }
    $content = $evt.message.content
    if ($null -eq $content -or $content -is [string]) { continue }
    foreach ($item in $content) {
      if ($item.type -eq 'tool_use' -and $item.name -eq 'Skill') { $navyk = $true }
      if ($evt.type -eq 'assistant' -and $item.type -eq 'text') {
        $questions += ([regex]::Matches($item.text, '\?')).Count
      }
    }
  }
} elseif ($Env -eq 'kilo') {
  # М-17/М-18: раньше — подстрочный поиск имени навыка по всему текстовому
  # журналу, засчитывавший любое упоминание (в том числе в прозе модели без
  # вызова) — прибор сам объявлен негодным (docs/reviews/2026-08-23-core-review.md).
  # Теперь читаем структурный признак из --format json: событие tool_use с
  # part.tool == "skill" и именем навыка в part.state.input.name — тот же
  # класс сигнала, что и tool_use "Skill" у Claude. Имя может прийти как
  # голое ("developing-1c-configurations") либо с префиксом плагина
  # ("1c-agent-skills:developing-1c-configurations", О-3 в docs/plan.md) —
  # проверяется совпадение по хвосту, а не по точному имени.
  $navyk = $false
  $questions = 0
  $names = @()
  foreach ($line in ($txt -split "`r?`n")) {
    $line = $line.Trim()
    if (-not $line) { continue }
    try { $evt = $line | ConvertFrom-Json -ErrorAction Stop } catch { continue }
    if ($evt.type -eq 'tool_use' -and $evt.part.tool -eq 'skill') {
      $name = [string]$evt.part.state.input.name
      if ($name -match $skillPattern) {
        $navyk = $true
        # Имя нужно отдельно от признака: «сработал хоть какой-то навык»
        # и «сработал нужный» — разные вопросы, и при выборе между вариантами
        # определения раздела ответ даёт только второй.
        $names += ($name -replace '^.*:', '')
      }
    }
    if ($evt.type -eq 'text' -and $evt.part.text) {
      $questions += ([regex]::Matches($evt.part.text, '\?')).Count
    }
  }
} else {
  # codex: структурный журнал для него не проверялся (только Kilo и Claude
  # — М-18 называет именно их), остаётся прежний подстрочный поиск.
  $navyk = [bool]($txt -match $skillSubstr)
  $questions = ([regex]::Matches($txt, '\?')).Count
}
if ($null -eq $names) { $names = @() }
[pscustomobject]@{
  Среда    = $Env
  Задача   = $Prompt.Substring(0, [Math]::Min(55, $Prompt.Length))
  Навык    = $navyk
  Навыки   = (($names | Select-Object -Unique) -join ', ')
  Вопросов = $questions
  Журнал   = $log
}
