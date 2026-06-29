param(
    [string]$PublicHostname = "",
    [switch]$SkipGitPull
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$StartScript = Join-Path $ScriptDir "start-cloudflare-windows.ps1"
$LocalEnv = Join-Path $ScriptDir "windows-local-env.ps1"
$LogsDir = Join-Path $Root "logs"
$OutLog = Join-Path $LogsDir "bracket-server.out.log"
$ErrLog = Join-Path $LogsDir "bracket-server.err.log"

if (Test-Path $LocalEnv) {
    . $LocalEnv
}

if (-not $PublicHostname -and $env:BRACKET_PUBLIC_HOSTNAME) {
    $PublicHostname = $env:BRACKET_PUBLIC_HOSTNAME
}

if (-not $PublicHostname) {
    throw "Public hostname is required. Pass -PublicHostname or set `$env:BRACKET_PUBLIC_HOSTNAME in scripts\windows-local-env.ps1."
}

Set-Location $Root

if (-not $SkipGitPull) {
    git pull
}

$listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
$processIds = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($processId in $processIds) {
    if ($processId) {
        Stop-Process -Id $processId -Force
        Write-Host "Stopped process $processId on port 8000."
    }
}

New-Item -ItemType Directory -Force $LogsDir | Out-Null

if (Test-Path $OutLog) {
    Remove-Item $OutLog -Force
}

if (Test-Path $ErrLog) {
    Remove-Item $ErrLog -Force
}

$arguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $StartScript,
    "-PublicHostname", $PublicHostname
)

$process = Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList $arguments `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -PassThru `
    -WindowStyle Hidden

Write-Host "Started bracket app process $($process.Id)."
Write-Host "Output log: $OutLog"
Write-Host "Error log:  $ErrLog"
Write-Host "Check status with: netstat -ano | findstr :8000"
