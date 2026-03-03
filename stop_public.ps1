$ErrorActionPreference = 'SilentlyContinue'

Set-Location $PSScriptRoot
$pidsFile = Join-Path $PSScriptRoot '.public_tunnel_pids.json'

if (-not (Test-Path $pidsFile)) {
    Write-Host 'No running tunnel metadata found (.public_tunnel_pids.json).' -ForegroundColor Yellow
    exit 0
}

$data = Get-Content $pidsFile -Raw | ConvertFrom-Json

if ($data.flask_pid) {
    Stop-Process -Id $data.flask_pid -Force
}

if ($data.tunnel_pid) {
    Stop-Process -Id $data.tunnel_pid -Force
}

Remove-Item $pidsFile -Force
Write-Host 'Flask + LocalTunnel stopped.' -ForegroundColor Green
