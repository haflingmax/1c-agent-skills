# Ставит навыки набора в Kilo и в Claude Code: прогоны должны идти на одном и том же.
$src = (Resolve-Path (Join-Path $PSScriptRoot '..\skills')).Path
foreach ($dst in @("$env:USERPROFILE\.config\kilo\skills",
                   "$env:USERPROFILE\.claude\skills")) {
  New-Item -ItemType Directory -Force $dst | Out-Null
  Get-ChildItem $src -Directory | ForEach-Object {
    $t = Join-Path $dst $_.Name
    if (Test-Path $t) { Remove-Item $t -Recurse -Force }
    Copy-Item $_.FullName $t -Recurse
  }
  "поставлено в {0}: {1} навыков" -f $dst, (Get-ChildItem $dst -Directory).Count
}

# Разрешаем навыки набора поимённо в списке разрешений Kilo.
#
# Без этого поставленный навык в режиме --auto до вызова не доходит и молчит:
# в блоке "skill" файла kilo.jsonc стоит "*": "ask", и не разрешённый поимённо
# навык выглядит как «не выбрался». Четыре прогона подряд — 1c-queries,
# 1c-security, 1c-managed-forms, 1c-access-rights — были засчитаны как отказ
# набора, хотя отказывал список разрешений. Разбор в комментарии run-prompt.ps1.
#
# Правка идёт по конфигу владельца, поэтому она хирургическая: дописываются
# только недостающие строки, комментарии и прочие блоки не трогаются, рядом
# кладётся запасная копия. Согласовано владельцем 26.08.2026.
$разрешение = Join-Path $PSScriptRoot 'allow-skills-in-kilo.py'
if (Test-Path $разрешение) {
  python $разрешение --каталог $src
} else {
  "[предупреждение] {0} не найден — список разрешений Kilo не тронут" -f $разрешение
}
