$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root 'backend\.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $python)) {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if (!$command) { throw 'Se necesita Python 3.11 para iniciar el motor.' }
    $python = $command.Source
}
& $python (Join-Path $PSScriptRoot 'engine.py') start
if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar el motor local.' }
