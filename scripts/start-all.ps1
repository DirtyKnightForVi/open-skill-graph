param(
    [ValidateSet("minimal", "registry", "redis", "full")]
    [string]$Mode = "minimal",
    [string]$EnvFile = ".env",
    [string]$SandboxEnvFile = "sandbox.env",
    [switch]$HealthOnly
)

$target = Join-Path $PSScriptRoot "win/start-all.ps1"
& $target -Mode $Mode -EnvFile $EnvFile -SandboxEnvFile $SandboxEnvFile -HealthOnly:$HealthOnly
