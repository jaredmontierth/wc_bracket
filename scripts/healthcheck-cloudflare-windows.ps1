param(
    [string]$PublicHostname = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$LocalEnv = Join-Path $ScriptDir "windows-local-env.ps1"
$UpdateScript = Join-Path $ScriptDir "update-cloudflare-windows.ps1"
$LogsDir = Join-Path $Root "logs"
$WatchdogLog = Join-Path $LogsDir "watchdog.log"
$LockFile = Join-Path $LogsDir "watchdog.lock"
$HealthUrl = "http://127.0.0.1:8000/api/health/"
$KeepLock = $false

if (Test-Path $LocalEnv) {
    . $LocalEnv
}

if (-not $PublicHostname -and $env:BRACKET_PUBLIC_HOSTNAME) {
    $PublicHostname = $env:BRACKET_PUBLIC_HOSTNAME
}

New-Item -ItemType Directory -Force $LogsDir | Out-Null

function Write-WatchdogLog($Message) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $WatchdogLog -Value "[$stamp] $Message"
}

if (Test-Path $LockFile) {
    $lockAge = (Get-Date) - (Get-Item $LockFile).LastWriteTime
    if ($lockAge.TotalMinutes -lt 15) {
        Write-WatchdogLog "Previous watchdog run is still active; skipping."
        exit 0
    }
    Write-WatchdogLog "Removing stale watchdog lock."
    Remove-Item $LockFile -Force
}

try {
    Set-Content -Path $LockFile -Value $PID
    $response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-WatchdogLog "Healthy."
        exit 0
    }

    Write-WatchdogLog "Unhealthy status $($response.StatusCode); restarting."
    $KeepLock = $true
}
catch {
    Write-WatchdogLog "Health check failed: $($_.Exception.Message); restarting."
    $KeepLock = $true
}
finally {
    if ((-not $KeepLock) -and (Test-Path $LockFile)) {
        Remove-Item $LockFile -Force
    }
}

$arguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $UpdateScript,
    "-SkipGitPull"
)

if ($PublicHostname) {
    $arguments += @("-PublicHostname", $PublicHostname)
}

Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList $arguments `
    -WorkingDirectory $Root `
    -WindowStyle Hidden

Write-WatchdogLog "Restart launched."
