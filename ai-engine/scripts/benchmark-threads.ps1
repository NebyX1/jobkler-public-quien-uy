[CmdletBinding()]
param([int]$Port = 8182)
$ErrorActionPreference = 'Stop'
$engine = Split-Path -Parent $PSScriptRoot
$root = Split-Path -Parent $engine
$server = Join-Path $engine 'bin\llama-server.exe'
$model = Join-Path $engine 'models\Qwen3.5-2B-Q4_K_M.gguf'
$settings = @{}
foreach ($line in Get-Content -LiteralPath (Join-Path $engine '.env')) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$') { $settings[$Matches[1]] = $Matches[2].Trim('"', "'") }
}
if (!$settings.LLM_API_KEY -or $settings.LLM_API_KEY.Length -lt 32) { throw 'Falta la clave local del motor.' }
if (!(Test-Path -LiteralPath $server) -or !(Test-Path -LiteralPath $model)) { throw 'Falta el servidor o el modelo local.' }
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
try { $listener.Start() } catch { throw "El puerto de benchmark $Port está ocupado; no se detuvo ningún proceso." } finally { $listener.Stop() }
$env:LLM_API_KEY = $settings.LLM_API_KEY
$env:LLAMA_API_KEY = $settings.LLM_API_KEY
$env:LLM_URL = "http://127.0.0.1:$Port"
$logs = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$results = @()
foreach ($threads in @(4, 6, 8, 12)) {
    $args = ('-m "{0}" --alias Qwen3.5-2B-Q4_K_M.gguf --host 127.0.0.1 --port {1} -c 4096 -np 1 -t {2} -tb {2} -ngl 0 --no-cache-prompt --reasoning off --metrics' -f $model, $Port, $threads)
    $process = Start-Process -FilePath $server -ArgumentList $args -WorkingDirectory $engine -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs "bench-$threads.out.log") -RedirectStandardError (Join-Path $logs "bench-$threads.err.log") -PassThru
    try {
        $ready = $false
        for ($i = 0; $i -lt 120; $i++) {
            if ($process.HasExited) { throw 'El servidor de benchmark terminó durante el arranque.' }
            try {
                $answer = Invoke-RestMethod -Uri "$env:LLM_URL/v1/models" -Headers @{ Authorization = "Bearer $env:LLM_API_KEY" } -TimeoutSec 2
                if ($answer.data.Count -gt 0) { $ready = $true; break }
            } catch { Start-Sleep -Milliseconds 500 }
        }
        if (!$ready) { throw 'El servidor de benchmark no alcanzó el estado listo.' }
        $started = Get-Date
        $before = Get-Process -Id $process.Id
        $cpuBefore = $before.TotalProcessorTime.TotalSeconds
        $measurement = node (Join-Path $engine 'scripts\benchmark.mjs') 'Explicá en una frase por qué los zorros se adaptan a distintos ambientes.' | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0) { throw 'La prueba de generación falló.' }
        $after = Get-Process -Id $process.Id
        $results += [pscustomobject]@{
            threads = $threads
            ttft_ms = [math]::Round($measurement.ttft_ms, 1)
            total_ms = [math]::Round($measurement.total_ms, 1)
            ram_mb = [math]::Round($after.WorkingSet64 / 1MB, 1)
            cpu_seconds = [math]::Round($after.TotalProcessorTime.TotalSeconds - $cpuBefore, 3)
            wall_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 2)
        }
    } finally {
        $owned = Get-CimInstance Win32_Process -Filter "ProcessId = $($process.Id)" -ErrorAction SilentlyContinue
        if ($owned -and $owned.ExecutablePath -eq $server) {
            Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
            Wait-Process -Id $process.Id -Timeout 5 -ErrorAction SilentlyContinue
        }
    }
}
$results | ConvertTo-Json -Depth 4
