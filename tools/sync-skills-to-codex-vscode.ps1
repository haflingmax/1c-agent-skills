# Переливает навыки набора в раздаточный каталог связки Codex + VS Code.
#
# Раздаточный каталог universal-ai-server/scripts/codex-vscode уезжает
# пользователю целиком, поэтому навыки лежат там копией, а не ссылкой и не
# скачиванием: у получателя нет ни этого репозитория, ни гарантии доступа к
# нашему GitHub, а origin/main на момент заведения скрипта отставал от
# рабочего дерева на 102 коммита. Установщик, который тянет из сети, привёз
# бы пользователю не те навыки, которые правились.
#
# Скрипт зовётся после правки навыков. Он ничего не спрашивает и никуда не
# ставит: только приводит копию в соответствие с skills/ и печатает, что
# изменилось. Пустой список изменений — законный и ожидаемый результат.

[CmdletBinding()]
param(
    [string]$Назначение
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# $PSScriptRoot в блоке param пуст, поэтому путь по умолчанию считается здесь.
# Раздаточный каталог лежит в соседнем репозитории рядом с этим.
if ([string]::IsNullOrWhiteSpace($Назначение)) {
    $Назначение = Join-Path $PSScriptRoot '..\..\universal-ai-server\scripts\codex-vscode\skills'
}

$источник = (Resolve-Path (Join-Path $PSScriptRoot '..\skills')).Path
$цель = [System.IO.Path]::GetFullPath($Назначение).TrimEnd('\')

# Каталог назначения удаляется целиком, поэтому сначала убеждаемся, что это
# действительно каталог навыков раздачи, а не что-то, на что случайно указали.
$лист = [System.IO.Path]::GetFileName($цель)
$родитель = [System.IO.Path]::GetFileName([System.IO.Path]::GetDirectoryName($цель))
if ($лист -ne 'skills' -or $родитель -ne 'codex-vscode') {
    throw "Отказ: путь назначения не похож на каталог раздачи (ожидалось .../codex-vscode/skills): $цель"
}

function Снимок {
    param([Parameter(Mandatory = $true)][string]$Корень)

    $итог = @{}
    if (-not (Test-Path -LiteralPath $Корень -PathType Container)) { return $итог }
    foreach ($файл in Get-ChildItem -LiteralPath $Корень -Recurse -File -Force) {
        $относительный = $файл.FullName.Substring($Корень.Length).TrimStart('\')
        if ($относительный -like '*__pycache__*') { continue }
        $итог[$относительный] = (Get-FileHash -LiteralPath $файл.FullName -Algorithm SHA256).Hash
    }
    return $итог
}

$было = Снимок -Корень $цель

if (Test-Path -LiteralPath $цель) {
    Remove-Item -LiteralPath $цель -Recurse -Force
}
$каталогРодителя = [System.IO.Path]::GetDirectoryName($цель)
New-Item -ItemType Directory -Force $каталогРодителя | Out-Null
Copy-Item -LiteralPath $источник -Destination $цель -Recurse -Force

# __pycache__ — след запуска скриптов навыка на машине разработки. В раздаче
# он бесполезен и только путает при сверке.
Get-ChildItem -LiteralPath $цель -Recurse -Directory -Force |
    Where-Object { $_.Name -eq '__pycache__' } |
    Remove-Item -Recurse -Force

$стало = Снимок -Корень $цель

$добавлено = @($стало.Keys | Where-Object { -not $было.ContainsKey($_) } | Sort-Object)
$удалено = @($было.Keys | Where-Object { -not $стало.ContainsKey($_) } | Sort-Object)
$изменено = @($стало.Keys |
    Where-Object { $было.ContainsKey($_) -and $было[$_] -ne $стало[$_] } |
    Sort-Object)

"источник:  {0}" -f $источник
"назначение: {0}" -f $цель
"навыков:   {0}, файлов: {1}" -f (Get-ChildItem -LiteralPath $цель -Directory).Count, $стало.Count

if ($добавлено.Count -eq 0 -and $удалено.Count -eq 0 -and $изменено.Count -eq 0) {
    "изменений нет — копия уже совпадала с skills/"
    return
}

foreach ($пара in @(
    @{ Метка = 'добавлено'; Список = $добавлено },
    @{ Метка = 'изменено '; Список = $изменено },
    @{ Метка = 'удалено  '; Список = $удалено }
)) {
    if ($пара.Список.Count -eq 0) { continue }
    "{0}: {1}" -f $пара.Метка.Trim(), $пара.Список.Count
    foreach ($имя in $пара.Список) { "  {0} {1}" -f $пара.Метка, $имя }
}
