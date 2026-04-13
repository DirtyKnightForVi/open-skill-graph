param(
    [int]$Port = 8001,
    [switch]$Migrate
)

$target = Join-Path $PSScriptRoot "win/start-metadata-registry.ps1"
& $target -Port $Port -Migrate:$Migrate
