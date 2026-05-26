param(
    [int]$Port = 3001,
    [string]$ApiBaseUrl = "http://localhost:5500",
    [string]$ChatUrl = "http://localhost:3000"
)

$Root = Resolve-Path "$PSScriptRoot\..\.."
. "$PSScriptRoot\dev_process.ps1"

$env:NEXT_PUBLIC_API_BASE_URL = $ApiBaseUrl
$env:NEXT_PUBLIC_CHAT_URL = $ChatUrl

Write-Host "Starting Ollive dashboard on http://localhost:$Port"
Write-Host "API base URL: $env:NEXT_PUBLIC_API_BASE_URL"
Write-Host "Chat URL: $env:NEXT_PUBLIC_CHAT_URL"

Stop-ListeningPort -Port $Port
Start-ManagedDevProcess `
    -FilePath "npm.cmd" `
    -ArgumentList @("run", "dev", "--", "-p", "$Port") `
    -WorkingDirectory "$Root\apps\dashboard"
