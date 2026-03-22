# Backend Production Deployment Guide

## Purpose

This guide documents the single Docker Compose release path for the repo. The stack now uses only `docker-compose.yml` so local and cloud-style deployment share the same service definitions.

## Main Files

- `docker-compose.yml`
- `Backend/Dockerfile.prod`
- `Backend/.dockerignore`
- `Frontend/Dockerfile.prod`
- `Frontend/nginx.prod.conf`
- `Frontend/.dockerignore`
- `tools/load_test.py`

## What Changed

- consolidated the old split compose setup into one `docker-compose.yml`
- kept the production backend image that runs `uvicorn` without `--reload`
- kept separate worker and beat runtime support through the same production backend image
- kept the frontend production image that builds Vite assets and serves them through `nginx`
- kept the `nginx` proxy rules so the frontend still forwards:
  - `/api/*`
  - `/token`
  - `/openapi.json`
  - `/docs`
  - `/redoc`
  - `/media/school-logos/*`
- added a one-shot `migrate` service so Alembic runs before backend, worker, and beat start
- corrected the Compose build contexts to use the real `Backend/` and `Frontend/` directory casing so Linux deployments do not fail on case-sensitive filesystems
- changed direct Postgres, Redis, Mailpit, pgAdmin, and backend port mappings to loopback by default for safer VM and cloud deployment
- kept the reusable concurrent load-test script for health, login, events, and mixed authenticated traffic

## Release Startup

1. prepare `.env` with real deployment values
2. build and start the release stack:

`docker compose up -d --build`

3. open the frontend at:

`http://localhost:${FRONTEND_PORT:-5173}`

4. open the backend docs through the frontend proxy at:

`http://localhost:${FRONTEND_PORT:-5173}/api/docs`

5. optional local admin tools:

`docker compose --profile tools up -d pgadmin`

## Runtime Notes

- the frontend is the intended public entrypoint
- the backend is also bound to loopback by default at `127.0.0.1:${BACKEND_PORT:-8000}` for direct smoke checks from the host
- PostgreSQL and Redis are bound to loopback only by default
- backend media and import storage remain on named volumes
- Celery worker and beat still require Redis and the same backend environment variables
- the default local SMTP target is `mailpit`; set `SMTP_*` values in `.env` for real email delivery

## Required Environment Review

Set these before a real cloud deployment:

- `SECRET_KEY`
- `LOGIN_URL`
- `CORS_ALLOWED_ORIGINS`
- `POSTGRES_PASSWORD`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_USE_TLS` if welcome emails or notifications must leave the host

## Load Testing

### Health-only smoke load

`python tools/load_test.py --base-url http://127.0.0.1:${FRONTEND_PORT:-5173} --scenario health --requests 50 --concurrency 10`

### Direct backend login load

`python tools/load_test.py --base-url http://127.0.0.1:${BACKEND_PORT:-8000} --scenario login --email your-user@example.com --password your-password --requests 100 --concurrency 20`

### Frontend-proxied mixed traffic

`python tools/load_test.py --base-url http://127.0.0.1:${FRONTEND_PORT:-5173} --api-prefix /api --scenario mixed --email your-user@example.com --password your-password --requests 100 --concurrency 20 --include-governance`

## Testing

- validate config:
  - `docker compose config -q`
- verify frontend build still passes:
  - `npm run build`
- verify backend tests still pass:
  - `Backend\\.venv\\Scripts\\python.exe -m pytest -q Backend/app/tests`
- verify the load-test tool help output:
  - `python tools/load_test.py --help`
- optional smoke checks after startup:
  - `GET /`
  - `GET /api/docs`
  - `GET /openapi.json`
  - `GET /health`
  - run `tools/load_test.py` in `health` mode first, then in `login` or `mixed` mode with a real account
