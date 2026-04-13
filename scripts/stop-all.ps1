param(
    [switch]$KeepRedis
)

$ErrorActionPreference = "Continue"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$runDir = Join-Path $repoRoot ".run"
$pidFiles = @(
    @{ Name = "main"; Path = (Join-Path $runDir "main.pid") },
    @{ Name = "sandbox"; Path = (Join-Path $runDir "sandbox.pid") },
    @{ Name = "metadata-registry"; Path = (Join-Path $runDir "metadata-registry.pid") }
)

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
if ((-not $KeepRedis) -and (Test-Path $statePath)) {
    try {
        $state = Get-Content $statePath -Encoding UTF8 | ConvertFrom-Json
        if ($state.redis_container) {
            $name = [string]$state.redis_container
            $exists = docker ps -a --filter "name=^/$name$" --format "{{.Names}}"
            if ($exists -eq $name) {
                docker stop $name | Out-Null
                Write-Host "[stop] redis container $name"
            }
        }
    }
    catch {
        Write-Warning "Failed to parse services.state.json: $_"
    }
}

Write-Host "[done] stop script completed"
