# World Cup Bracket Tracker

A private Django + React app for tracking 2026 FIFA Men's World Cup knockout brackets and scoring them with ESPN's bracket system.

## Stack

- Django backend with SQLite
- React frontend built with Vite
- ESPN scoreboard sync from `https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard`

## Scoring

- Round of 32: 25 points each
- Round of 16: 50 points each
- Quarterfinals: 100 points each
- Semifinals: 200 points each
- Final: 400 points
- Max score: 2000

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python backend/manage.py migrate
python backend/manage.py sync_espn
python backend/manage.py runserver
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL. The frontend proxies `/api` requests to Django.

## Render Deployment

This repo includes a `render.yaml` blueprint for a single Django web service plus
a Render Postgres database. The build script installs Python and Node
dependencies, builds the React app, collects static files, runs migrations, and
syncs ESPN/fallback match data.

Required Render environment variable:

```bash
BRACKET_DEV_PASSWORD=your-private-developer-password
```

Render generates `SECRET_KEY` and `DATABASE_URL` from the blueprint. Locally, the
app still falls back to SQLite when `DATABASE_URL` is absent.

After deployment, use the Render URL for invite links. Developer mode will use
the `BRACKET_DEV_PASSWORD` value configured in Render.

### Moving Local Brackets to Render

1. Open the local app and unlock developer mode in Settings.
2. Click **Export** in the Backup section to download the JSON backup.
3. Open the deployed Render app and unlock developer mode there.
4. Click **Import** in the Backup section and select the JSON backup.

The import updates existing brackets by slug, so importing the same backup again
will refresh those brackets instead of creating duplicates.

## Free Windows Hosting With Cloudflare Tunnel

This path keeps the app on a Windows PC, uses local SQLite, and exposes it
through Cloudflare Tunnel without opening router ports.

### Start the App on Windows

From PowerShell in the project folder:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\start-cloudflare-windows.ps1 -PublicHostname "bracket.example.com"
```

Replace `bracket.example.com` with your real Cloudflare hostname. The script
will install dependencies, build React, run migrations, sync matches, and serve
Django at `http://127.0.0.1:8000`.

For a temporary Cloudflare quick tunnel, omit `-PublicHostname`:

```powershell
.\scripts\start-cloudflare-windows.ps1
```

### Pull Updates and Restart Over SSH

On the Windows PC, copy the example local config once:

```powershell
Copy-Item .\scripts\windows-local-env.example.ps1 .\scripts\windows-local-env.ps1
notepad .\scripts\windows-local-env.ps1
```

Set your real `BRACKET_PUBLIC_HOSTNAME`, `BRACKET_DEV_PASSWORD`, and
`SECRET_KEY`. The `windows-local-env.ps1` file is ignored by git.

After that, from SSH you can update and restart with:

```powershell
cd C:\Users\YOURUSER\Documents\YOUR-REPO
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\update-cloudflare-windows.ps1
```

The update script runs `git pull`, stops whatever is listening on port `8000`,
and starts the app again in the background. Logs are written to `logs\`.

### Create the Tunnel

For a stable invite URL, create a named Cloudflare Tunnel and route a public
hostname to:

```text
http://127.0.0.1:8000
```

An example config file is available at
`scripts/cloudflared-config.example.yml`.

Quick tunnels are fine for testing, but the `trycloudflare.com` URL changes
when the tunnel restarts. Use a named tunnel plus a Cloudflare-managed hostname
before sending invite links.
