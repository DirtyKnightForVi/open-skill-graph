param(
    [int]$Port = 8001,
    [switch]$Migrate
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "Missing command: uv"
}

if ($Migrate) {
    uv run python .\django_registry\manage.py migrate
}

Write-Host "[start] Metadata Registry Service -> 0.0.0.0:$Port"
uv run python .\django_registry\manage.py runserver 0.0.0.0:$Port
