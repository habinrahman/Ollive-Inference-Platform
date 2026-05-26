param(
    [int]$Port = 3000,
    [string]$ApiBaseUrl = "http://localhost:5500",
    [string]$DashboardUrl = "http://localhost:3001"
)

$Root = Resolve-Path "$PSScriptRoot\..\.."
. "$PSScriptRoot\dev_process.ps1"

$env:NEXT_PUBLIC_API_BASE_URL = $ApiBaseUrl
$env:NEXT_PUBLIC_DASHBOARD_URL = $DashboardUrl

Write-Host "Starting Ollive chat frontend on http://localhost:$Port"
Write-Host "API base URL: $env:NEXT_PUBLIC_API_BASE_URL"
Write-Host "Dashboard URL: $env:NEXT_PUBLIC_DASHBOARD_URL"

Stop-ListeningPort -Port $Port
Start-ManagedDevProcess `
    -FilePath "npm.cmd" `
    -ArgumentList @("run", "dev", "--", "-p", "$Port") `
    -WorkingDirectory "$Root\apps\frontend"
