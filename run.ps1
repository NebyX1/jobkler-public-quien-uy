[CmdletBinding()]
param(
    [int]$ApiPort = 0,
    [int]$WebPort = 0,
    [switch]$NoWait
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root 'backend'
$StateDir = Join-Path $Root '.jobkler'
$LogDir = Join-Path $Root 'logs'
$Venv = Join-Path $Backend '.venv'
$StartedApi = $null
$StartedWeb = $null
$StartedIndexer = $null
$StartedEngine = $false
$EngineScript = Join-Path $Root 'ai-engine\engine.py'
$KeepRunning = $false
$ApiPidFile = Join-Path $StateDir 'api.pid'
$WebPidFile = Join-Path $StateDir 'web.pid'
$IndexerPidFile = Join-Path $StateDir 'indexer.pid'

function Get-SystemPython {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        $path = (& $launcher.Source -3.11 -c 'import sys; print(sys.executable)').Trim()
        if ($LASTEXITCODE -eq 0 -and $path) { return $path }
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        $version = (& $python.Source --version 2>&1 | Out-String).Trim()
        if ($version -match '^Python 3\.11\.') { return $python.Source }
    }
    throw 'Se necesita Python 3.11. Instalalo o habilitá el launcher py -3.11.'
}

function Test-PortFree([int]$Port) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    try { $listener.Start(); return $true }
    catch { return $false }
    finally { $listener.Stop() }
}

function Get-TrackedProcess([string]$PidPath, [string]$ExpectedCommand) {
    if (!(Test-Path -LiteralPath $PidPath)) { return $null }
    $idText = (Get-Content -LiteralPath $PidPath -Raw).Trim()
    $id = 0
    if (![int]::TryParse($idText, [ref]$id)) { return $null }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $id" -ErrorAction SilentlyContinue
    if (!$process -or !$process.CommandLine -or $process.CommandLine -notlike "*$ExpectedCommand*") { return $null }
    return $process
}

function Stop-OwnedProcess([int]$ProcessId, [string]$ExpectedCommand) {
    if ($ProcessId -le 0) { return }
    $current = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if ($current -and $current.CommandLine -like "*$ExpectedCommand*") {
        Stop-Process -Id $ProcessId -ErrorAction SilentlyContinue
        Wait-Process -Id $ProcessId -Timeout 5 -ErrorAction SilentlyContinue
    }
}

try {
    $node = Get-Command node -ErrorAction SilentlyContinue
    if (!$node) { throw 'Node.js 22.15.1 es necesario. Instalalo antes de iniciar Jobkler.' }
    $nodeVersion = (& $node.Source --version).Trim()
    if ($nodeVersion -notmatch '^v(\d+)\.(\d+)\.') { throw 'No se pudo identificar la versión de Node.js.' }
    $nodeMajor = [int]$Matches[1]
    $nodeMinor = [int]$Matches[2]
    if ($nodeMajor -ne 22 -or $nodeMinor -lt 12) { throw "Node.js $nodeVersion no es compatible; se requiere Node 22.15.1 o 22.12+." }

    $SystemPython = Get-SystemPython
    $pythonVersion = (& $SystemPython --version 2>&1 | Out-String).Trim()
    if ($pythonVersion -notmatch '^Python 3\.11\.') { throw "Se requiere Python 3.11; se encontró $pythonVersion." }

    & $SystemPython (Join-Path $Root 'scripts\prepare_local.py')
    if ($LASTEXITCODE -ne 0) { throw 'La configuración local no pasó la validación; no se ejecutó ninguna migración.' }
    & $SystemPython $EngineScript prepare | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar la configuración del motor local.' }

    $portArgs = @()
    if ($ApiPort -gt 0) { $portArgs += @('--api-port', "$ApiPort") }
    if ($WebPort -gt 0) { $portArgs += @('--web-port', "$WebPort") }
    $settings = @(& $SystemPython (Join-Path $Root 'scripts\local_ports.py') @portArgs)
    if ($LASTEXITCODE -ne 0 -or $settings.Count -lt 3) { throw 'No se pudieron resolver los puertos locales.' }
    $ApiPort = [int]$settings[0]
    $WebPort = [int]$settings[1]
    $FrontendUrl = $settings[2]
    $FrontendOrigin = $FrontendUrl.TrimEnd('/')
    $BackendUrl = "http://127.0.0.1:$ApiPort"

    if (!(Test-PortFree $ApiPort)) { throw "El puerto API $ApiPort ya está ocupado. Revisá el proceso que lo usa; Jobkler no lo detuvo." }
    if (!(Test-PortFree $WebPort)) { throw "El puerto web $WebPort ya está ocupado. Revisá el proceso que lo usa; Jobkler no lo detuvo." }

    New-Item -ItemType Directory -Force -Path $StateDir, $LogDir, (Join-Path $Backend 'instance') | Out-Null
    if (!(Test-Path -LiteralPath $Venv)) {
        & $SystemPython -m venv $Venv
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear backend/.venv.' }
    }
    $VenvPython = Join-Path $Venv 'Scripts\python.exe'
    if (!(Test-Path -LiteralPath $VenvPython)) { throw 'El entorno Python local no contiene python.exe.' }
    $requirements = Join-Path $Backend 'requirements.txt'
    $stamp = Join-Path $Venv '.requirements-installed'
    if (!(Test-Path -LiteralPath $stamp) -or (Get-Item $requirements).LastWriteTimeUtc -gt (Get-Item $stamp).LastWriteTimeUtc) {
        & $VenvPython -m pip install -r $requirements
        if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias Flask.' }
        Set-Content -LiteralPath $stamp -Value (Get-Date -Format o) -NoNewline
    }

    $lock = Join-Path $Root 'package-lock.json'
    $installedLock = Join-Path $Root 'node_modules\.package-lock.json'
    if (!(Test-Path -LiteralPath $installedLock) -or (Get-Item $lock).LastWriteTimeUtc -gt (Get-Item $installedLock).LastWriteTimeUtc) {
        Push-Location $Root
        try { npm ci; if ($LASTEXITCODE -ne 0) { throw 'npm ci falló. Revisá package.json y package-lock.json.' } }
        finally { Pop-Location }
    }

    $env:APP_ENV = 'development'
    $env:APP_HOST = '127.0.0.1'
    $env:APP_PORT = "$ApiPort"
    $env:FRONTEND_URL = $FrontendOrigin
    $env:FUSIONAUTH_REDIRECT_URI = "$BackendUrl/api/auth/callback"
    $env:AUTH_ALLOWED_REDIRECT_URLS = $FrontendOrigin
    $env:JOBKLER_API_TARGET = $BackendUrl
    $env:VITE_PORT = "$WebPort"

    Push-Location $Backend
    try {
        & $VenvPython -m flask --app wsgi:app db upgrade
        if ($LASTEXITCODE -ne 0) { throw 'Alembic no pudo aplicar las migraciones locales.' }
    & $VenvPython -m flask --app wsgi:app seed-jobkler
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo inicializar la semilla local.' }
    & $VenvPython -m flask --app wsgi:app seed-search-fixtures
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron inicializar los fixtures sintéticos de búsqueda.' }
    & $VenvPython -m flask --app wsgi:app seed-expanded-profiles
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron inicializar los perfiles ficticios ampliados.' }
    & $VenvPython -m flask --app wsgi:app seed-rich-search-profiles
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron inicializar los perfiles detallados de búsqueda.' }
    & $VenvPython -m flask --app wsgi:app search-rebuild
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron sincronizar los documentos locales de búsqueda.' }
    & $VenvPython -m flask --app wsgi:app search-model-prepare
    $modelReady = $LASTEXITCODE -eq 0
    if (!$modelReady) { Write-Warning 'El encoder no está listo; la búsqueda avanzada seguirá disponible por texto y mostrará su modo reducido.' }
    if ($modelReady) {
        & $VenvPython -m flask --app wsgi:app search-reranker-prepare
        if ($LASTEXITCODE -ne 0) { Write-Warning 'El reranker no está listo; la búsqueda principal seguirá disponible.' }
    }
    $engineOutput = @(& $SystemPython $EngineScript start)
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar el motor local; revisá el diagnóstico anterior.' }
    $engineState = ($engineOutput -join "`n") | ConvertFrom-Json
    $StartedEngine = [bool]$engineState.started
    if ($engineState.managed) { Write-Host 'Motor Qwen local: listo.' }
    else { Write-Host 'Motor Qwen: configuración externa.' }
    & $VenvPython -m flask --app wsgi:app search-check-llm
} finally { Pop-Location }

    $wsgiPath = Join-Path $Backend 'wsgi.py'
    $apiLog = Join-Path $LogDir 'api.log'
    $apiError = Join-Path $LogDir 'api-error.log'
    $StartedApi = Start-Process -FilePath $VenvPython -ArgumentList ('"{0}"' -f $wsgiPath) -WorkingDirectory $Backend -WindowStyle Hidden -PassThru -RedirectStandardOutput $apiLog -RedirectStandardError $apiError
    Set-Content -LiteralPath $ApiPidFile -Value $StartedApi.Id

    $apiReady = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if ($StartedApi.HasExited) { throw "Flask terminó durante el arranque. Revisá $apiError." }
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri "$BackendUrl/api/health/ready" -TimeoutSec 2
            if ($response.StatusCode -eq 200) { $apiReady = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (!$apiReady) { throw "Flask no alcanzó readiness. Revisá $apiLog y $apiError." }

    if ($modelReady) {
        $indexerLog = Join-Path $LogDir 'indexer.log'
        $indexerError = Join-Path $LogDir 'indexer-error.log'
        $StartedIndexer = Start-Process -FilePath $VenvPython -ArgumentList '-m flask --app wsgi:app search-worker' -WorkingDirectory $Backend -WindowStyle Hidden -PassThru -RedirectStandardOutput $indexerLog -RedirectStandardError $indexerError
        Set-Content -LiteralPath $IndexerPidFile -Value $StartedIndexer.Id
        Start-Sleep -Seconds 2
        if ($StartedIndexer.HasExited) {
            Write-Warning "El worker de indexación no quedó activo. Revisá $indexerError; la recuperación textual sigue disponible."
            $StartedIndexer = $null
            Remove-Item -LiteralPath $IndexerPidFile -Force -ErrorAction SilentlyContinue
        }
    }

    $vitePath = Join-Path $Root 'node_modules\vite\bin\vite.js'
    $webLog = Join-Path $LogDir 'web.log'
    $webError = Join-Path $LogDir 'web-error.log'
    $viteArgs = ('"{0}" --host 127.0.0.1 --port {1} --strictPort' -f $vitePath, $WebPort)
    $StartedWeb = Start-Process -FilePath $node.Source -ArgumentList $viteArgs -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput $webLog -RedirectStandardError $webError
    Set-Content -LiteralPath $WebPidFile -Value $StartedWeb.Id

    $webReady = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if ($StartedWeb.HasExited) { throw "Vite terminó durante el arranque. Revisá $webError." }
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $FrontendUrl -TimeoutSec 2
            if ($response.StatusCode -eq 200) { $webReady = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (!$webReady) { throw "Vite no respondió. Revisá $webLog y $webError." }

    $KeepRunning = $true
    Write-Host "Jobkler está listo: $FrontendUrl"
    Write-Host "Flask readiness: $BackendUrl/api/health/ready"
    Write-Host "Logs: $LogDir"
    if ($modelReady -and $StartedIndexer) { Write-Host 'Indexador semántico local: activo.' }
    Start-Process $FrontendUrl

    if ($NoWait) { return }
    Write-Host 'Presioná Ctrl+C para detener solo los procesos de Jobkler.'
    while ($true) {
        if ($StartedApi.HasExited) { throw "Flask se detuvo. Revisá $apiError." }
        if ($StartedWeb.HasExited) { throw "Vite se detuvo. Revisá $webError." }
        Start-Sleep -Seconds 2
    }
} catch {
    Write-Error $_
    exit 1
} finally {
    if (!$KeepRunning -or !$NoWait) {
        if ($StartedWeb) {
            Stop-OwnedProcess $StartedWeb.Id $vitePath
            Remove-Item -LiteralPath $WebPidFile -Force -ErrorAction SilentlyContinue
        }
        if ($StartedIndexer) {
            Stop-OwnedProcess $StartedIndexer.Id $VenvPython
            Remove-Item -LiteralPath $IndexerPidFile -Force -ErrorAction SilentlyContinue
        }
        if ($StartedApi) {
            Stop-OwnedProcess $StartedApi.Id $wsgiPath
            Remove-Item -LiteralPath $ApiPidFile -Force -ErrorAction SilentlyContinue
        }
        if ($StartedEngine) { & $SystemPython $EngineScript stop | Out-Null }
    }
}
