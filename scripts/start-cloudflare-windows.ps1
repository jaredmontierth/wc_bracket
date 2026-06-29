param(
    [string]$PublicHostname = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$Backend = Join-Path $Root "backend"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

Set-Location $Root

if (-not (Test-Path $VenvPython)) {
    py -3 -m venv .venv
}

if (-not $env:BRACKET_DEV_PASSWORD) {
    $SecurePassword = Read-Host "Developer password for Settings" -AsSecureString
    $PasswordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
    try {
        $env:BRACKET_DEV_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($PasswordPointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($PasswordPointer)
    }
}

if (-not $env:SECRET_KEY) {
    $env:SECRET_KEY = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
}

$env:DEBUG = "False"
$env:SECURE_SSL_REDIRECT = "False"

if ($PublicHostname) {
    $env:ALLOWED_HOSTS = "localhost,127.0.0.1,$PublicHostname"
    $env:CSRF_TRUSTED_ORIGINS = "https://$PublicHostname"
}
else {
    $env:ALLOWED_HOSTS = "localhost,127.0.0.1,.trycloudflare.com"
    $env:CSRF_TRUSTED_ORIGINS = "https://*.trycloudflare.com"
}

& $VenvPython -m pip install -r requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend

& $VenvPython backend/manage.py collectstatic --no-input
& $VenvPython backend/manage.py migrate
& $VenvPython backend/manage.py sync_espn

Write-Host ""
Write-Host "Bracket app is starting on http://127.0.0.1:8000"
Write-Host "Point Cloudflare Tunnel at http://127.0.0.1:8000"
Write-Host ""

Set-Location $Backend
& $VenvPython serve_waitress.py
