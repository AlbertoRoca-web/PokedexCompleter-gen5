param(
    [int]$Port = 8787,
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$WindowTitle = "PokedexCompleter Backend"
)

$ErrorActionPreference = "Stop"

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

Write-Host "[backend-restart] Repo: $RepoRoot"
Write-Host "[backend-restart] Port: $Port"
Write-Host "[backend-restart] Window title: $WindowTitle"

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

$cmd = "title $WindowTitle && cd /d `"$RepoRoot`" && git pull --ff-only && uv run rld serve --host 127.0.0.1 --port $Port"
Write-Host "[backend-restart] Launching fresh backend window..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $cmd -WorkingDirectory $RepoRoot

$deadline = (Get-Date).AddSeconds(30)
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

Write-Error "Backend did not become healthy on port $Port before timeout."
exit 1
