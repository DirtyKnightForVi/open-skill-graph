param(
    [ValidateSet("minimal", "registry", "redis", "full")]
    [string]$Mode = "minimal",
    [string]$EnvFile = ".env",
    [string]$SandboxEnvFile = "sandbox.env",
    [switch]$HealthOnly
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "../..")
Set-Location $repoRoot

$runDir = Join-Path $repoRoot ".run"
$logDir = Join-Path $runDir "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

function Read-KeyValueFile {
    param(
        [string]$Path,
        [hashtable]$Defaults
    )

    $config = @{}
    foreach ($k in $Defaults.Keys) {
        $config[$k] = $Defaults[$k]
    }

    if (-not (Test-Path $Path)) {
        return $config
    }

    $lines = Get-Content $Path -Encoding UTF8
    foreach ($raw in $lines) {
        $line = $raw.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }

        $parts = $line.Split("=", 2)
        if ($parts.Count -ne 2) {
            continue
        }

        $key = $parts[0].Trim()
        $value = $parts[1].Trim()

        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        $config[$key] = $value
    }

    return $config
}

function Parse-UrlHostPort {
    param(
        [string]$Url,
        [string]$DefaultHost,
        [int]$DefaultPort
    )

    if (-not $Url) {
        return @{ Host = $DefaultHost; Port = $DefaultPort }
    }

    try {
        $uri = [Uri]$Url
        $host = if ($uri.Host) { $uri.Host } else { $DefaultHost }
        $port = if ($uri.Port -gt 0) { $uri.Port } else { $DefaultPort }
        return @{ Host = $host; Port = $port }
    }
    catch {
        return @{ Host = $DefaultHost; Port = $DefaultPort }
    }
}

function Test-TcpPort {
    param(
        [string]$Host,
        [int]$Port,
        [int]$TimeoutMs = 800
    )

    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect($Host, $Port, $null, $null)
        if (-not $iar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
            $client.Close()
            return $false
        }
        $client.EndConnect($iar)
        $client.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Wait-PortReady {
    param(
        [string]$Name,
        [string]$Host,
        [int]$Port,
        [int]$Retry = 40
    )

    for ($i = 0; $i -lt $Retry; $i++) {
        if (Test-TcpPort -Host $Host -Port $Port) {
            Write-Host "[ok] $Name is ready at $Host:$Port"
            return $true
        }
        Start-Sleep -Seconds 1
    }

    return $false
}

function Assert-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing command: $Name"
    }
}

function Start-ServiceShell {
    param(
        [string]$Name,
        [string]$Command
    )

    $logPath = Join-Path $logDir "$Name.log"
    $pidPath = Join-Path $runDir "$Name.pid"

    $escapedRoot = $repoRoot.Path.Replace("'", "''")
    $escapedLog = $logPath.Replace("'", "''")
    $wrapped = "Set-Location '$escapedRoot'; `$Host.UI.RawUI.WindowTitle='osg-$Name'; & { $Command } *>> '$escapedLog'"

    $proc = Start-Process -FilePath "powershell" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", $wrapped
    ) -PassThru -WorkingDirectory $repoRoot

    $proc.Id | Set-Content -Path $pidPath -Encoding UTF8
    Write-Host "[start] $Name started (pid=$($proc.Id), log=$logPath)"
}

function Is-LocalHost {
    param([string]$Host)
    return @("127.0.0.1", "localhost", "::1", "0.0.0.0") -contains $Host.ToLower()
}

function Check-AndReport {
    param(
        [string]$Name,
        [string]$Host,
        [int]$Port,
        [bool]$Required
    )
    $ok = Test-TcpPort -Host $Host -Port $Port
    $reqLabel = if ($Required) { "required" } else { "optional" }
    $status = if ($ok) { "OK" } else { "FAILED" }
    Write-Host "[check] $Name $Host:$Port [$reqLabel] -> $status"
    return $ok
}

Assert-Command -Name "uv"

$defaults = @{
    "SANDBOX_SERVICE_URL" = "http://127.0.0.1:8000"
    "SESSION_TYPE" = "json"
    "REDIS_HOST" = "127.0.0.1"
    "REDIS_PORT" = "6379"
    "SKILL_METADATA_SOURCE" = "meta"
    "REGISTRY_BASE_URL" = "http://127.0.0.1:8001"
}
$cfg = Read-KeyValueFile -Path $EnvFile -Defaults $defaults

$sandbox = Parse-UrlHostPort -Url $cfg["SANDBOX_SERVICE_URL"] -DefaultHost "127.0.0.1" -DefaultPort 8000
$registry = Parse-UrlHostPort -Url $cfg["REGISTRY_BASE_URL"] -DefaultHost "127.0.0.1" -DefaultPort 8001
$redisHost = if ($cfg["REDIS_HOST"]) { $cfg["REDIS_HOST"] } else { "127.0.0.1" }
$redisPort = [int]$cfg["REDIS_PORT"]
$mainHost = "127.0.0.1"
$mainPort = 3000

$needRegistry = $Mode -in @("registry", "full")
$needRedis = $Mode -in @("redis", "full")

Write-Host "[mode] $Mode"
Write-Host "[config] sandbox=$($sandbox.Host):$($sandbox.Port), registry=$($registry.Host):$($registry.Port), redis=$redisHost:$redisPort"

if ($cfg["SKILL_METADATA_SOURCE"].ToLower() -eq "registry" -and -not $needRegistry) {
    Write-Warning "Current .env uses SKILL_METADATA_SOURCE=registry, but mode=$Mode does not start registry."
}
if ($cfg["SESSION_TYPE"].ToLower() -eq "redis" -and -not $needRedis) {
    Write-Warning "Current .env uses SESSION_TYPE=redis, but mode=$Mode does not start redis."
}

$checks = @(
    @{ Name = "sandbox"; Host = $sandbox.Host; Port = $sandbox.Port; Required = $true },
    @{ Name = "main"; Host = $mainHost; Port = $mainPort; Required = $false }
)
if ($needRegistry) {
    $checks += @{ Name = "metadata-registry"; Host = $registry.Host; Port = $registry.Port; Required = $true }
}
if ($needRedis) {
    $checks += @{ Name = "redis"; Host = $redisHost; Port = $redisPort; Required = $true }
}

$failedRequired = @()
foreach ($c in $checks) {
    $ok = Check-AndReport -Name $c.Name -Host $c.Host -Port $c.Port -Required $c.Required
    if ((-not $ok) -and $c.Required) {
        $failedRequired += "$($c.Name)($($c.Host):$($c.Port))"
    }
}

if ($HealthOnly) {
    if ($failedRequired.Count -gt 0) {
        throw "Health check failed. Missing required services: $($failedRequired -join ', ')"
    }
    Write-Host "[done] health-only check passed"
    exit 0
}

if (-not (Test-TcpPort -Host $sandbox.Host -Port $sandbox.Port)) {
    Start-ServiceShell -Name "sandbox" -Command "uv run --env-file $SandboxEnvFile .\\sandbox_service.py"
    if (-not (Wait-PortReady -Name "sandbox" -Host $sandbox.Host -Port $sandbox.Port)) {
        throw "Sandbox not ready at $($sandbox.Host):$($sandbox.Port). See .run/logs/sandbox.log"
    }
}
else {
    Write-Host "[skip] sandbox already running at $($sandbox.Host):$($sandbox.Port)"
}

if ($needRegistry) {
    if (-not (Test-TcpPort -Host $registry.Host -Port $registry.Port)) {
        $registryCmd = "uv run python .\\django_registry\\manage.py migrate; uv run python .\\django_registry\\manage.py runserver 0.0.0.0:$($registry.Port)"
        Start-ServiceShell -Name "metadata-registry" -Command $registryCmd
        if (-not (Wait-PortReady -Name "metadata-registry" -Host $registry.Host -Port $registry.Port)) {
            throw "Metadata registry not ready at $($registry.Host):$($registry.Port). See .run/logs/metadata-registry.log"
        }
    }
    else {
        Write-Host "[skip] metadata-registry already running at $($registry.Host):$($registry.Port)"
    }
}

$redisContainer = "open-skill-graph-redis"
if ($needRedis) {
    if (Is-LocalHost -Host $redisHost) {
        if (-not (Test-TcpPort -Host $redisHost -Port $redisPort)) {
            Assert-Command -Name "docker"
            $exists = docker ps -a --filter "name=^/$redisContainer$" --format "{{.Names}}"
            if ($exists -eq $redisContainer) {
                docker start $redisContainer | Out-Null
                Write-Host "[start] redis container restarted: $redisContainer"
            }
            else {
                docker run -d --name $redisContainer -p "$redisPort`:6379" redis:7-alpine | Out-Null
                Write-Host "[start] redis container created: $redisContainer (host port $redisPort)"
            }

            if (-not (Wait-PortReady -Name "redis" -Host $redisHost -Port $redisPort)) {
                throw "Redis not ready at $redisHost:$redisPort"
            }
        }
        else {
            Write-Host "[skip] redis already running at $redisHost:$redisPort"
        }
    }
    else {
        if (-not (Test-TcpPort -Host $redisHost -Port $redisPort)) {
            throw "Redis host is remote and unreachable: $redisHost:$redisPort"
        }
        Write-Host "[ok] remote redis reachable at $redisHost:$redisPort"
    }
}

if (-not (Test-TcpPort -Host $mainHost -Port $mainPort)) {
    Start-ServiceShell -Name "main" -Command "uv run python .\\main.py"
    if (-not (Wait-PortReady -Name "main" -Host $mainHost -Port $mainPort)) {
        throw "Main service not ready at $mainHost:$mainPort. See .run/logs/main.log"
    }
}
else {
    Write-Host "[skip] main already running at $mainHost:$mainPort"
}

$state = [ordered]@{
    started_at = (Get-Date).ToString("s")
    mode = $Mode
    env_file = $EnvFile
    sandbox = "$($sandbox.Host):$($sandbox.Port)"
    metadata_registry = "$($registry.Host):$($registry.Port)"
    redis = "$redisHost:$redisPort"
    redis_container = if ($needRedis -and (Is-LocalHost -Host $redisHost)) { $redisContainer } else { "" }
    main = "$mainHost:$mainPort"
}
$state | ConvertTo-Json | Set-Content -Path (Join-Path $runDir "services.state.json") -Encoding UTF8

Write-Host "[done] startup finished. main=http://$mainHost:$mainPort"
