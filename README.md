# Homebase

Django app for browsing MLB standings, rosters, player stats, news, and leaderboards. Data comes live from MLB's public StatsAPI and RSS feeds.

## Running locally

Requires Python 3.13+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createcachetable
python manage.py runserver
```

Open http://127.0.0.1:8000/.

## Tech Stack

Django 5.2, Bootstrap 5.3, Plotly, Postgres (SQLite locally).

## Caching

API and RSS responses are cached in the database via Django's built-in cache framework. Standings and leaders cache for 5 minutes, team and player metadata for 24 hours, and news feeds for 10 minutes. The cache table is created by running `python manage.py createcachetable`.
