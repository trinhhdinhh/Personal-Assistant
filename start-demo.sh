#!/usr/bin/env bash
# Start the whole demo with one command:
#   1. the Postgres database (Docker)
#   2. fresh synthetic data built around today (60 days of history + the coming week)
#   3. the Django backend (localhost:8000) and the Next.js dashboard (localhost:3000)
#
#   ./start-demo.sh
#
# Press Ctrl+C to stop both servers. The database keeps running (docker compose stop to stop it).
set -euo pipefail
cd "$(dirname "$0")"

echo "→ Starting the database"
docker compose up -d db
until docker compose exec -T db pg_isready -U postgres -q; do sleep 1; done

cd backend
echo "→ Preparing the database and today's synthetic data"
../.venv/bin/python manage.py migrate --noinput
../.venv/bin/python manage.py seed_synthetic
../.venv/bin/python manage.py seed_demo_suggestions

echo "→ Starting the backend on http://localhost:8000"
../.venv/bin/python manage.py runserver &
backend=$!
trap 'kill $backend 2>/dev/null' EXIT

cd ../frontend
echo "→ Starting the dashboard on http://localhost:3000"
npm run dev
