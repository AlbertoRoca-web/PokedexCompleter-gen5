[CmdletBinding()]
param(
    [string]$Name = "PokedexCompleterAgent"
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $root
try {
    uv sync --extra desktop
    uv run pyinstaller `
        --noconfirm `
        --clean `
        --onefile `
        --name $Name `
        --collect-all pokedex_completer_gen5 `
        scripts/local_companion.py
    Write-Host "Built dist/$Name.exe"
} finally {
    Pop-Location
}
