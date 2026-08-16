param(
    [int]$Port = 8787,
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

Write-Host "[backend-restart] Repo: $RepoRoot"
Write-Host "[backend-restart] Port: $Port"

$portConnections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
$portPids = @($portConnections | Select-Object -ExpandProperty OwningProcess -Unique)
foreach ($pidValue in $portPids) {
    if ($pidValue -and $pidValue -ne $PID) {
        Write-Host "[backend-restart] Killing process on port ${Port}: PID $pidValue"
        Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
    }
}

$escapedRepo = $RepoRoot.Replace("\", "\\")
$repoCmds = Get-CimInstance Win32_Process -Filter "name = 'cmd.exe'" |
    Where-Object {
        ($_.CommandLine -like "*$RepoRoot*") -or
        ($_.CommandLine -match $escapedRepo) -or
        ($_.CommandLine -like "*rld serve*") -or
        ($_.CommandLine -like "*PokedexCompleter-gen5*")
    }

foreach ($process in $repoCmds) {
    if ($process.ProcessId -ne $PID) {
        Write-Host "[backend-restart] Closing old repo cmd.exe PID $($process.ProcessId)"
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

$cmd = "cd /d `"$RepoRoot`" && git pull --ff-only && uv run rld serve --host 127.0.0.1 --port $Port"
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
