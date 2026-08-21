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
    $exe = "$env:USERPROFILE\.vscode\extensions\kilocode.kilo-code-7.4.22\bin\kilo.exe"
    & $exe run --auto --dir $Dir $Prompt *> $log
  }
  'claude' {
    Push-Location $Dir; try { claude -p $Prompt *> $log } finally { Pop-Location }
  }
  'codex' {
    Push-Location $Dir
    try { codex exec --profile tpm --skip-git-repo-check $Prompt *> $log } finally { Pop-Location }
  }
}
$txt = if (Test-Path $log) { Get-Content $log -Raw -Encoding Unicode } else { '' }
[pscustomobject]@{
  Среда    = $Env
  Задача   = $Prompt.Substring(0, [Math]::Min(55, $Prompt.Length))
  Навык    = [bool]($txt -match 'developing-1c-configurations|1c-build-and-db')
  Вопросов = ([regex]::Matches($txt, '\?')).Count
  Журнал   = $log
}
