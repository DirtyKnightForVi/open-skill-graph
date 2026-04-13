# Backward-compatible alias. Prefer start-metadata-registry.ps1.
param(
    [int]$Port = 8001,
    [switch]$Migrate
)

& (Join-Path $PSScriptRoot "start-metadata-registry.ps1") -Port $Port -Migrate:$Migrate
