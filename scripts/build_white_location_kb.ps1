[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SavePath,
    [string]$OutputPath = "data/knowledge/white-catchable-locations.json",
    [ValidateSet("direct", "obtainable")]
    [string]$Mode = "direct",
    [int]$DelayMilliseconds = 100
)

$ErrorActionPreference = "Stop"
$SavePath = $SavePath.Trim("'")
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$output = Join-Path $root $OutputPath
$exporter = Join-Path $root "scripts/export_catchable_targets.py"

$env:RLD_SAVE_PATH = $SavePath
$reportJson = & uv run python $exporter --game white --mode $Mode | Out-String
Remove-Item Env:RLD_SAVE_PATH
$report = $reportJson | ConvertFrom-Json
$targets = @($report.targets)
$records = [System.Collections.Generic.List[object]]::new()

foreach ($target in $targets) {
    $url = "https://pokeapi.co/api/v2/pokemon/$($target.national)/encounters"
    Write-Host "Fetching $($target.name) (#$($target.national))"
    $encounters = @(Invoke-RestMethod -Uri $url -Method Get)
    $locations = [System.Collections.Generic.List[object]]::new()
    foreach ($encounter in $encounters) {
        $versions = @($encounter.version_details | Where-Object {
            $_.version.name -in @("white", "black-white")
        })
        if ($versions.Count -eq 0) { continue }
        $details = foreach ($version in $versions) {
            foreach ($detail in @($version.encounter_details)) {
                [ordered]@{
                    method = $detail.method.name
                    min_level = $detail.min_level
                    max_level = $detail.max_level
                    chance = $detail.chance
                    conditions = @($detail.condition_values.name)
                }
            }
        }
        $locations.Add([ordered]@{
            location_area = $encounter.location_area.name
            location_url = $encounter.location_area.url
            encounters = @($details)
        })
    }
    $records.Add([ordered]@{
        national = [int]$target.national
        regional = [int]$target.regional
        name = $target.name
        target_method = $target.method
        category = $target.category
        owned = $target.national -in @($report.owned_target_ids)
        locations = @($locations)
        source = $url
    })
    Start-Sleep -Milliseconds $DelayMilliseconds
}

$knowledgeBase = [ordered]@{
    schema_version = 1
    generated_at = [DateTime]::UtcNow.ToString("o")
    game = "white"
    mode = $Mode
    save_path = $SavePath
    source = "PokeAPI pokemon encounter endpoints via PowerShell Invoke-RestMethod"
    target_count = $records.Count
    missing_target_count = @($report.missing_targets).Count
    fly_policy = [ordered]@{
        menu_toggle_button = "S"
        party_action = "Open Pokemon menu -> select Unfezant -> select Fly"
        requirement = "Only use Fly when it shortens the route to a required Living Dex target."
    }
    targets = @($records)
}

New-Item -ItemType Directory -Force -Path (Split-Path $output -Parent) | Out-Null
$knowledgeBase | ConvertTo-Json -Depth 12 | Set-Content -Path $output -Encoding UTF8
Write-Host "Wrote $output"
