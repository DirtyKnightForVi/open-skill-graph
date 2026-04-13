param(
    [ValidateSet("all", "minimal", "registry", "redis", "full")]
    [string]$Mode = "all",
    [switch]$KeepRedis
)

$target = Join-Path $PSScriptRoot "win/stop-all.ps1"
& $target -Mode $Mode -KeepRedis:$KeepRedis
