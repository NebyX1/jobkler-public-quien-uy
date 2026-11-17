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

$engineScript = Join-Path $Root 'ai-engine\engine.py'
$enginePython = Join-Path $Root 'backend\.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $enginePython)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    $enginePython = if ($pythonCommand) { $pythonCommand.Source } else { $null }
}
if ($enginePython -and (Test-Path -LiteralPath $engineScript)) {
    $engineResult = @(& $enginePython $engineScript stop)
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo detener el motor local de Jobkler.' }
    $engineState = ($engineResult -join "`n") | ConvertFrom-Json
    if ($engineState.stopped) { Write-Host 'Motor Qwen local detenido.' }
} elseif (Test-Path -LiteralPath (Join-Path $StateDir 'ai-engine.pid')) {
    Write-Warning 'No hay Python disponible para verificar y detener el motor local.'
}
