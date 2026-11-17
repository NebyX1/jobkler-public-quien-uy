$ErrorActionPreference = 'Stop'
$engine = Split-Path -Parent $PSScriptRoot
$root = Split-Path -Parent $engine
$settings = @{}
foreach ($line in Get-Content -LiteralPath (Join-Path $engine '.env')) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$') { $settings[$Matches[1]] = $Matches[2].Trim('"', "'") }
}
if (!$settings.LLM_API_KEY) { throw 'Falta la clave local del motor.' }
$env:LLM_API_KEY = $settings.LLM_API_KEY
$port = if ($settings.LLM_PORT) { $settings.LLM_PORT } else { '8081' }
$env:LLM_URL = "http://127.0.0.1:$port"
$pidFile = Join-Path $root '.jobkler\ai-engine.pid'
if (!(Test-Path -LiteralPath $pidFile)) { throw 'Iniciá el motor integrado antes del benchmark.' }
$record = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
$owned = Get-CimInstance Win32_Process -Filter "ProcessId = $([int]$record.pid)" -ErrorAction SilentlyContinue
if (!$owned -or $owned.ExecutablePath -ne (Join-Path $engine 'bin\llama-server.exe')) { throw 'El proceso registrado no coincide con el motor integrado.' }
$prompts = @(
    'Explica en español, en aproximadamente 150 palabras, qué es una base de datos relacional y menciona tres ejemplos prácticos de uso.',
    'Explica las diferencias principales entre una base de datos SQL y una base de datos NoSQL. Responde de forma clara, técnica y breve.',
    'Soy un usuario que quiere encontrar información dentro de una colección de documentos. Explica cómo podrías ayudarme utilizando una herramienta de búsqueda de texto.'
)
$results = @()
foreach ($prompt in $prompts) {
    $before = Get-Process -Id $record.pid
    $cpuBefore = $before.TotalProcessorTime.TotalSeconds
    $measurement = node (Join-Path $engine 'scripts\benchmark.mjs') $prompt | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'La prueba de generación falló.' }
    $after = Get-Process -Id $record.pid
    $results += [pscustomobject]@{
        prompt = $prompt
        ttft_ms = [math]::Round($measurement.ttft_ms, 1)
        total_ms = [math]::Round($measurement.total_ms, 1)
        chars = $measurement.chars
        ram_mb = [math]::Round($after.WorkingSet64 / 1MB, 1)
        cpu_seconds = [math]::Round($after.TotalProcessorTime.TotalSeconds - $cpuBefore, 3)
    }
}
$results | ConvertTo-Json -Depth 4
