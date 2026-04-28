# CI Docker Build Fix (April 2026)

## What changed

- **Removed seeder service from `docker-compose.prod.yml`** on the `main` branch.
  - Per repository rules, the `seeder/` folder and service should only exist on the `pilot` branch.
  - The seeder Dockerfile uses `FROM aura-backend:production`, creating a build-order dependency that `docker compose build` cannot resolve during CI, causing the "Docker Build Test" job to fail.

- **Removed seeder env file copies from `.github/workflows/ci.yml`**.
  - Both the `compose-config` and `docker-build` jobs previously copied `seeder/.env.example` to `seeder/.env`. This is no longer needed since the seeder service is removed from the production compose.

## Affected files

- `docker-compose.prod.yml`: Removed `seeder` service block (lines 65-74).
- `.github/workflows/ci.yml`: Removed `cp seeder/.env.example seeder/.env` from both CI env file creation steps.

## How to test

Push to `main` and verify the CI/CD pipeline passes all jobs:
- Validate Compose ✅
- Backend Checks ✅
- Backend Tests ✅
- Assistant Tests ✅
- Frontend Checks ✅
- Docker Build Test ✅ (previously failing)
- Deploy to Production ✅
