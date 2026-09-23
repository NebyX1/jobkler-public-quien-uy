$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$StateDir = Join-Path $Root '.jobkler'

function Stop-Tracked([string]$Name, [string]$ScriptPath) {
    $pidFile = Join-Path $StateDir "$Name.pid"
    if (!(Test-Path -LiteralPath $pidFile)) { return }
    $id = 0
    if (![int]::TryParse((Get-Content -LiteralPath $pidFile -Raw).Trim(), [ref]$id)) {
        Remove-Item -LiteralPath $pidFile -Force
        return
    }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $id" -ErrorAction SilentlyContinue
    if (!$process) {
        Remove-Item -LiteralPath $pidFile -Force
        Write-Host "$($Name): proceso ya detenido."
        return
    }
    if (!$process.CommandLine -or $process.CommandLine -notlike "*$ScriptPath*") {
        Remove-Item -LiteralPath $pidFile -Force
        Write-Warning "${Name}: el PID guardado no pertenece a este Jobkler; no se detuvo ningún proceso."
        return
    }
    Stop-Process -Id $id -ErrorAction SilentlyContinue
    Wait-Process -Id $id -Timeout 5 -ErrorAction SilentlyContinue
    $stillOwned = Get-CimInstance Win32_Process -Filter "ProcessId = $id" -ErrorAction SilentlyContinue
    if ($stillOwned -and $stillOwned.CommandLine -like "*$ScriptPath*") {
        Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    Write-Host "$Name detenido."
}

if (!(Test-Path -LiteralPath $StateDir)) {
    Write-Host 'No hay procesos Jobkler registrados.'
    exit 0
}
$wsgiPath = Join-Path $Root 'backend\wsgi.py'
$indexerPython = Join-Path $Root 'backend\.venv\Scripts\python.exe'
$vitePath = Join-Path $Root 'node_modules\vite\bin\vite.js'
Stop-Tracked 'indexer' $indexerPython
Stop-Tracked 'web' $vitePath
Stop-Tracked 'api' $wsgiPath
