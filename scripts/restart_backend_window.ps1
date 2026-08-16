param(
    [int]$Port = 8787,
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$WindowTitle = "PokedexCompleter Backend"
)

$ErrorActionPreference = "Stop"
$RuntimeDir = Join-Path $RepoRoot ".runtime\backend-window"
$BackendLog = Join-Path $RuntimeDir "backend.log"
$BackendCmd = Join-Path $RuntimeDir "run-backend.cmd"

function Stop-ProcessTree {
    param([int]$ProcessIdToStop)

    if (-not $ProcessIdToStop -or $ProcessIdToStop -eq $PID) {
        return
    }

    $existing = Get-Process -Id $ProcessIdToStop -ErrorAction SilentlyContinue
    if (-not $existing) {
        Write-Host "[backend-restart] PID $ProcessIdToStop already gone."
        return
    }

    Write-Host "[backend-restart] Killing process tree PID $ProcessIdToStop"
    $taskkillOutput = & taskkill.exe /PID $ProcessIdToStop /T /F 2>&1
    $exitCode = $LASTEXITCODE
    if ($taskkillOutput) {
        $taskkillOutput | ForEach-Object { Write-Host $_ }
    }
    if ($exitCode -ne 0 -and $exitCode -ne 128) {
        Write-Host "[backend-restart] taskkill exit code for PID ${ProcessIdToStop}: $exitCode"
    }
}

function Wait-ProcessGone {
    param(
        [int[]]$ProcessIds,
        [int]$TimeoutSeconds = 10
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $stillRunning = @($ProcessIds | Where-Object { $_ -and (Get-Process -Id $_ -ErrorAction SilentlyContinue) })
        if ($stillRunning.Count -eq 0) {
            return $true
        }
        Start-Sleep -Milliseconds 250
    }
    return $false
}

function Wait-PortFree {
    param(
        [int]$PortToCheck,
        [int]$TimeoutSeconds = 10
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $connections = @(Get-NetTCPConnection -LocalPort $PortToCheck -ErrorAction SilentlyContinue)
        if ($connections.Count -eq 0) {
            return $true
        }
        Start-Sleep -Milliseconds 250
    }
    return $false
}

function Get-BackendLogTail {
    if (-not (Test-Path $BackendLog)) {
        return "[backend-restart] Backend log does not exist yet: $BackendLog"
    }
    return (Get-Content $BackendLog -Tail 80 -ErrorAction SilentlyContinue) -join "`n"
}

Write-Host "[backend-restart] Repo: $RepoRoot"
Write-Host "[backend-restart] Port: $Port"
Write-Host "[backend-restart] Window title: $WindowTitle"
Write-Host "[backend-restart] Log: $BackendLog"

$portConnections = @(Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue)
$portPids = @($portConnections | Select-Object -ExpandProperty OwningProcess -Unique)

$escapedRepo = $RepoRoot.Replace("\", "\\")
$cmdProcessIds = @(
    Get-CimInstance Win32_Process -Filter "name = 'cmd.exe'" |
        Where-Object {
            ($_.CommandLine -like "*$WindowTitle*") -or
            ($_.CommandLine -like "*$RepoRoot*") -or
            ($_.CommandLine -match $escapedRepo) -or
            ($_.CommandLine -like "*rld serve*") -or
            ($_.CommandLine -like "*PokedexCompleter-gen5*")
        } |
        Select-Object -ExpandProperty ProcessId -Unique
)

$windowProcessIds = @(
    Get-Process -Name "cmd" -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowTitle -like "*$WindowTitle*" } |
        Select-Object -ExpandProperty Id -Unique
)

$processesToKill = @($portPids + $cmdProcessIds + $windowProcessIds) |
    Where-Object { $_ -and $_ -ne $PID } |
    Sort-Object -Unique

foreach ($processId in $processesToKill) {
    Stop-ProcessTree -ProcessIdToStop $processId
}

if ($processesToKill.Count -gt 0) {
    $gone = Wait-ProcessGone -ProcessIds $processesToKill -TimeoutSeconds 10
    if (-not $gone) {
        Write-Error "Old backend process/window did not close before timeout. Refusing to launch a new one."
        exit 1
    }
}

$portFree = Wait-PortFree -PortToCheck $Port -TimeoutSeconds 10
if (-not $portFree) {
    Write-Error "Port $Port is still occupied after stopping old backend. Refusing to launch a new window."
    exit 1
}

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
Set-Content -Path $BackendLog -Value "[backend-restart] Starting backend at $(Get-Date -Format o)" -Encoding UTF8

$cmd = @"
@echo off
title $WindowTitle
cd /d "$RepoRoot"
echo [backend-restart] Repo %CD% >> "$BackendLog" 2>>&1
echo [backend-restart] Pulling latest code... >> "$BackendLog" 2>>&1
git pull --ff-only >> "$BackendLog" 2>>&1
if errorlevel 1 goto failed
echo [backend-restart] Starting server... >> "$BackendLog" 2>>&1
uv run rld serve --host 127.0.0.1 --port $Port >> "$BackendLog" 2>>&1
goto end
:failed
echo [backend-restart] Command failed before server startup. >> "$BackendLog" 2>>&1
:end
echo [backend-restart] Backend command exited. >> "$BackendLog" 2>>&1
"@
Set-Content -Path $BackendCmd -Value $cmd -Encoding ASCII

Write-Host "[backend-restart] Launching fresh backend window..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", "`"$BackendCmd`"" -WorkingDirectory $RepoRoot

$deadline = (Get-Date).AddSeconds(45)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2
        Write-Host "[backend-restart] Health OK: $($response | ConvertTo-Json -Compress)"
        exit 0
    } catch {
        Write-Host "[backend-restart] Waiting for health..."
    }
}

Write-Host "[backend-restart] Backend log tail:"
Write-Host (Get-BackendLogTail)
Write-Error "Backend did not become healthy on port $Port before timeout."
exit 1
