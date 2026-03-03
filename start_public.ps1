param(
    [string]$Subdomain = 'smartparking-rafal'
)

$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $pythonExe)) {
    Write-Host 'Python virtual environment not found at .venv\Scripts\python.exe' -ForegroundColor Red
    exit 1
}

$flaskOutLog = Join-Path $PSScriptRoot 'flask.out.log'
$flaskErrLog = Join-Path $PSScriptRoot 'flask.err.log'
$tunnelOutLog = Join-Path $PSScriptRoot 'tunnel.out.log'
$tunnelErrLog = Join-Path $PSScriptRoot 'tunnel.err.log'
$pidsFile = Join-Path $PSScriptRoot '.public_tunnel_pids.json'

if (Test-Path $flaskOutLog) { Remove-Item $flaskOutLog -Force }
if (Test-Path $flaskErrLog) { Remove-Item $flaskErrLog -Force }
if (Test-Path $tunnelOutLog) { Remove-Item $tunnelOutLog -Force }
if (Test-Path $tunnelErrLog) { Remove-Item $tunnelErrLog -Force }

Write-Host 'Starting Flask server on port 5000...' -ForegroundColor Cyan
$flaskProc = Start-Process -FilePath $pythonExe -ArgumentList 'app.py' -PassThru -WindowStyle Hidden -RedirectStandardOutput $flaskOutLog -RedirectStandardError $flaskErrLog

$ready = $false
for ($i = 0; $i -lt 25; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $listen = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction Stop
        if ($listen) {
            $ready = $true
            break
        }
    } catch {
    }
}

if (-not $ready) {
    Write-Host 'Flask did not start listening on port 5000. Check flask.out.log / flask.err.log' -ForegroundColor Red
    exit 1
}

Write-Host "Starting LocalTunnel (requested subdomain: $Subdomain)..." -ForegroundColor Cyan
$tunnelArgs = "localtunnel --port 5000 --subdomain $Subdomain"
$tunnelProc = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c',"npx $tunnelArgs" -PassThru -WindowStyle Hidden -RedirectStandardOutput $tunnelOutLog -RedirectStandardError $tunnelErrLog

$url = $null
$fallbackStarted = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 500
    if ((Test-Path $tunnelOutLog) -or (Test-Path $tunnelErrLog)) {
        $logText = ''
        if (Test-Path $tunnelOutLog) { $logText += (Get-Content $tunnelOutLog -Raw) }
        if (Test-Path $tunnelErrLog) { $logText += "`n" + (Get-Content $tunnelErrLog -Raw) }
        if (-not $fallbackStarted -and ($logText -match 'subdomain.*(unavailable|taken|already)')) {
            Write-Host "Subdomain '$Subdomain' is unavailable. Falling back to random URL..." -ForegroundColor Yellow
            Stop-Process -Id $tunnelProc.Id -Force -ErrorAction SilentlyContinue
            if (Test-Path $tunnelOutLog) { Remove-Item $tunnelOutLog -Force }
            if (Test-Path $tunnelErrLog) { Remove-Item $tunnelErrLog -Force }
            $tunnelProc = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','npx localtunnel --port 5000' -PassThru -WindowStyle Hidden -RedirectStandardOutput $tunnelOutLog -RedirectStandardError $tunnelErrLog
            $fallbackStarted = $true
            continue
        }
        $line = @()
        if (Test-Path $tunnelOutLog) {
            $line = Get-Content $tunnelOutLog | Select-String -Pattern 'your url is:' | Select-Object -Last 1
        }
        if ($line) {
            $url = ($line.ToString() -replace '.*your url is:\s*', '').Trim()
            break
        }
    }
}

@{
    flask_pid = $flaskProc.Id
    tunnel_pid = $tunnelProc.Id
    requested_subdomain = $Subdomain
    started_at = (Get-Date).ToString('s')
} | ConvertTo-Json | Set-Content $pidsFile -Encoding UTF8

if ($url) {
    Write-Host ''
    Write-Host 'Public URL:' -ForegroundColor Green
    Write-Host $url -ForegroundColor Yellow
    if ($url -like "https://$Subdomain.loca.lt") {
        Write-Host "Fixed URL active: https://$Subdomain.loca.lt" -ForegroundColor Green
    }
    Write-Host ''
    Write-Host 'If LocalTunnel asks for a password, open:' -ForegroundColor Cyan
    Write-Host 'https://loca.lt/mytunnelpassword' -ForegroundColor Yellow
    Write-Host ''
    Write-Host 'To stop everything, run: .\stop_public.ps1' -ForegroundColor Cyan
} else {
    Write-Host 'Tunnel started but URL not detected yet. Check tunnel.out.log / tunnel.err.log' -ForegroundColor Yellow
    Write-Host 'To stop everything, run: .\stop_public.ps1' -ForegroundColor Cyan
}
