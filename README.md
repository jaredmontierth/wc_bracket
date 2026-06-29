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
