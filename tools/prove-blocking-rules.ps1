# Доказывает запуском на живой платформе каждое правило проверяльщика
# check-1c-cli.py — и то, чем он блокирует, и то, что он обязан пропускать.
# Правило имеет право блокировать, только если платформа не делает заявленного;
# если делает — правилу место в предупреждениях (правило 11 архитектуры).
#
# Ожидание процесса здесь с таймаутом, а не голым -Wait: один из проверяемых
# случаев (пакетный ключ конфигуратора в режиме ENTERPRISE) не завершается
# никогда — платформа открывает сеанс и ждёт человека. Голый -Wait на нём
# вешает прогон навсегда, а сам факт незавершения и есть доказательство.
param(
  [string]$Exe = "C:\Program Files\1cv8\8.3.27.2325\bin\1cv8.exe",
  [string]$Base = "D:\1C\base\trade",
  [string]$Work = "$env:TEMP\1c-proof",
  [int]$TimeoutSec = 60
)
New-Item -ItemType Directory -Force $Work | Out-Null

# <CF> в списке ключей заменяется на путь выгрузки этого случая.
function Run1C($name, $argv) {
  $log = Join-Path $Work "$name.log"; $rc = Join-Path $Work "$name.rc"
  $cf  = Join-Path $Work "$name.cf"
  Remove-Item $log,$rc,$cf -ErrorAction SilentlyContinue
  $a = @($argv | ForEach-Object { if ($_ -eq '<CF>') { $cf } else { $_ } })
  $a += @('/DisableStartupDialogs','/Out',$log,'/DumpResult',$rc)
  $p = Start-Process -FilePath $Exe -ArgumentList $a -PassThru -NoNewWindow -WorkingDirectory $Work
  $null = $p.Handle
  $done = $p.WaitForExit($TimeoutSec * 1000)
  if (-not $done) { try { $p.Kill() } catch {}; $null = $p.WaitForExit(10000) }
  [pscustomobject]@{
    Имя        = $name
    КодВыхода  = if ($done) { $p.ExitCode } else { "не завершился за $TimeoutSec с, убит" }
    DumpResult = if (Test-Path $rc) { (Get-Content $rc -Raw).Trim() } else { 'нет' }
    ФайлСоздан = Test-Path $cf
    Размер     = if (Test-Path $cf) { (Get-Item $cf).Length } else { 0 }
    Журнал     = if (Test-Path $log) { ((@(Get-Content $log -Encoding Default)) -join ' ').Trim() } else { 'нет' }
  }
}

$r = @(
  # Пропускать обязан: платформа это принимает и делает.
  Run1C 'канон'               @('DESIGNER','/F',$Base,'/DumpCfg','<CF>')
  Run1C 'строчными'           @('DESIGNER','/F',$Base,'/dumpcfg','<CF>')
  Run1C 'строчный-ключ-базы'  @('DESIGNER','/f',$Base,'/dumpcfg','<CF>')
  Run1C 'строка-соединения'   @('DESIGNER','/IBConnectionString',"File=$Base;",'/DumpCfg','<CF>')
  Run1C 'ключ-чужого-режима'  @('DESIGNER','/F',$Base,'/UsePrivilegedMode','/DumpCfg','<CF>')
  Run1C 'опция-чужого-ключа'  @('DESIGNER','/F',$Base,'/DumpCfg','<CF>','-Format','Hierarchical')
  # Блокировать имеет право: платформа заявленного не делает.
  Run1C 'выдуманный'          @('DESIGNER','/F',$Base,'/DumpCfgToFile','<CF>')
  Run1C 'без-базы'            @('DESIGNER','/DumpCfg','<CF>')
  Run1C 'без-режима'          @('/F',$Base,'/DumpCfg','<CF>')
  Run1C 'заглушка-пути'       @('DESIGNER','/F','d:/<каталог базы>','/DumpCfg','<CF>')
  Run1C 'конфигуратор-в-enterprise' @('ENTERPRISE','/F',$Base,'/LoadCfg',(Join-Path $Work 'канон.cf'))
)
$r | Format-Table -AutoSize
$r | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $Work 'proof.json') -Encoding utf8
