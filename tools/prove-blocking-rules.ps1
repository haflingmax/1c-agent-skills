# Доказывает каждое блокирующее правило проверяльщика запуском на живой платформе.
# Правило имеет право блокировать, только если платформа не делает заявленного.
param(
  [string]$Exe = "C:\Program Files\1cv8\8.3.27.2325\bin\1cv8.exe",
  [string]$Base = "D:\1C\base\trade",
  [string]$Work = "$env:TEMP\1c-proof"
)
New-Item -ItemType Directory -Force $Work | Out-Null

function Run1C($name, $keys) {
  $log = Join-Path $Work "$name.log"; $rc = Join-Path $Work "$name.rc"
  $cf  = Join-Path $Work "$name.cf"
  Remove-Item $log,$rc,$cf -ErrorAction SilentlyContinue
  $a = @('DESIGNER','/F',$Base) + $keys + @($cf,'/DisableStartupDialogs','/Out',$log,'/DumpResult',$rc)
  $p = Start-Process -FilePath $Exe -ArgumentList $a -Wait -PassThru -NoNewWindow
  [pscustomobject]@{
    Имя        = $name
    КодВыхода  = $p.ExitCode
    DumpResult = if (Test-Path $rc) { (Get-Content $rc -Raw).Trim() } else { 'нет' }
    ФайлСоздан = Test-Path $cf
    Журнал     = if (Test-Path $log) { ((Get-Content $log -Encoding Default -Raw) -replace "`r?`n",' ').Trim() } else { 'нет' }
  }
}

$r = @(
  Run1C 'канон'      @('/DumpCfg')
  Run1C 'строчными'  @('/dumpcfg')
  Run1C 'выдуманный' @('/DumpCfgToFile')
)
$r | Format-Table -AutoSize
$r | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $Work 'proof.json') -Encoding utf8
