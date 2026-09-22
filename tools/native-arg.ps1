# Escapes a string so that Windows PowerShell 5.1 passes it to a native
# program (kilo.exe, claude.exe, node behind codex.ps1) as ONE argument, intact.
#
# PowerShell 5.1 does not escape embedded double quotes when it builds the
# native command line. Measured 22.09.2026 with node as the receiver:
#   'a "b c" d'  arrives as  'a b'   -- quotes lost, the prompt is cut short;
#   'x("R.T")'   arrives as  'x(R.T)' -- quotes lost silently.
# The verification prompt V1 reached all three agents without the quotes
# around "РегистрНакопления.ТоварыНаСкладах", and two of them commented on it.
#
# Rules are the MSVCRT/CommandLineToArgvW ones: a quote becomes \" and every
# backslash run right before a quote is doubled; a trailing backslash run is
# doubled too, because PowerShell wraps an argument with spaces in quotes.
function ConvertTo-NativeArgument([string]$Text) {
  $s = [regex]::Replace($Text, '(\\*)"', { param($m) ($m.Groups[1].Value * 2) + '\"' })
  $s = [regex]::Replace($s, '(\\+)$', { param($m) $m.Groups[1].Value * 2 })
  return $s
}
