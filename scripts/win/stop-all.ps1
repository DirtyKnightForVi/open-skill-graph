param(
    [ValidateSet("all", "minimal", "registry", "redis", "full")]
    [string]$Mode = "all",
    [switch]$KeepRedis
)

$ErrorActionPreference = "Continue"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "../..")
Set-Location $repoRoot

$runDir = Join-Path $repoRoot ".run"

$stopMain = $Mode -in @("all", "minimal", "registry", "redis", "full")
$stopSandbox = $Mode -in @("all", "minimal", "registry", "redis", "full")
$stopRegistry = $Mode -in @("all", "registry", "full")
$stopRedis = ($Mode -in @("all", "redis", "full")) -and (-not $KeepRedis)

$pidFiles = @()
if ($stopMain) { $pidFiles += @{ Name = "main"; Path = (Join-Path $runDir "main.pid") } }
if ($stopSandbox) { $pidFiles += @{ Name = "sandbox"; Path = (Join-Path $runDir "sandbox.pid") } }
if ($stopRegistry) { $pidFiles += @{ Name = "metadata-registry"; Path = (Join-Path $runDir "metadata-registry.pid") } }

foreach ($item in $pidFiles) {
    if (Test-Path $item.Path) {
        $raw = Get-Content $item.Path -ErrorAction SilentlyContinue
        $pid = 0
        if ([int]::TryParse($raw, [ref]$pid) -and $pid -gt 0) {
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($proc) {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Host "[stop] $($item.Name) (pid=$pid)"
            }
        }
        Remove-Item $item.Path -Force -ErrorAction SilentlyContinue
    }
}

$statePath = Join-Path $runDir "services.state.json"
if ($stopRedis -and (Test-Path $statePath)) {
    try {
        $state = Get-Content $statePath -Encoding UTF8 | ConvertFrom-Json
        if ($state.redis_container) {
            $name = [string]$state.redis_container
            if (Get-Command docker -ErrorAction SilentlyContinue) {
                $exists = docker ps -a --filter "name=^/$name$" --format "{{.Names}}"
                if ($exists -eq $name) {
                    docker stop $name | Out-Null
                    Write-Host "[stop] redis container $name"
                }
            }
        }
    }
    catch {
        Write-Warning "Failed to parse services.state.json: $_"
    }
}

Write-Host "[done] stop script completed (mode=$Mode)"
