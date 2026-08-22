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
