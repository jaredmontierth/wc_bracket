#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend

python backend/manage.py collectstatic --no-input
python backend/manage.py migrate
python backend/manage.py sync_espn
