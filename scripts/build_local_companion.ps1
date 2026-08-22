[CmdletBinding()]
param(
    [string]$Name = "PokedexCompleterAgent",
    [switch]$NoSync
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $root
try {
    if (-not $NoSync) {
        uv sync --extra desktop
    }
    uv run --no-sync pyinstaller `
        --noconfirm `
        --clean `
        --onefile `
        --name $Name `
        --paths src `
        --collect-all pokedex_completer_gen5 `
        scripts/local_companion.py
    Write-Host "Built dist/$Name.exe"
} finally {
    Pop-Location
}
