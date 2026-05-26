param(
    [int]$Port = 8000
)

$Root = Resolve-Path "$PSScriptRoot\..\.."
. "$PSScriptRoot\dev_process.ps1"

$EnvFile = Join-Path $Root ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $Line = $_.Trim()
        if ($Line -and -not $Line.StartsWith("#") -and $Line.Contains("=")) {
            $Parts = $Line.Split("=", 2)
            [Environment]::SetEnvironmentVariable($Parts[0], $Parts[1], "Process")
        }
    }
}

$env:PYTHONPATH = "$Root\packages\llm_sdk;$Root\apps\api"
$env:INGESTION_ENDPOINT = "http://localhost:$Port/v1/ingest/events"

Write-Host "Starting Ollive API on http://127.0.0.1:$Port"
Write-Host "Telemetry ingestion endpoint: $env:INGESTION_ENDPOINT"
Write-Host "Mock provider mode: $env:ALLOW_MOCK_PROVIDER"

Stop-ListeningPort -Port $Port
Start-ManagedDevProcess `
    -FilePath "python" `
    -ArgumentList @(
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "$Port",
        "--app-dir",
        "$Root\apps\api"
    ) `
    -WorkingDirectory "$Root\apps\api"
