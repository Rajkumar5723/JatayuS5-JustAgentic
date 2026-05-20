# Hiresy

Hiresy is an AI-assisted hiring workflow platform for job posting, candidate applications, proctored assessments, live interviews, background verification, offer generation, and onboarding.

## What it includes

- HR job posting with configurable staged interview pipelines
- Candidate application forms with resume and cover-letter upload support
- Proctored `MCQ Test`, `Aptitude Test`, coding rounds, vibe coding, and live HR interviews
- Display-only `Group Discussion` round support in interview configuration
- QR-gated 360 room scan and malpractice evidence capture
- BGV with document upload, OCR extraction, and HR review
- Offer letter generation, candidate signature flow, and onboarding tracking

## Architecture

The app runs as a six-service stack:

- `frontend`
- `main-api`
- `evaluator`
- `shortlisting-test`
- `coding-test`
- `live-hr`

The repo is a monorepo with two deploy roots:

- `Frontend/` for the React app
- `Backend/` for all Python services

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker if you want to build the Railway images locally
- PostgreSQL on AWS RDS
- AWS S3 bucket for documents and evidence
- Redis if you use the configured Celery URLs
- Tesseract OCR if you want scanned-image OCR locally outside Docker

## Environment setup

1. Copy `.env.example` to `.env`.
2. Fill in:
   - `AWS_DATABASE_URL`
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_REGION`
   - `AWS_S3_BUCKET`
   - `S3_EVIDENCE_BUCKET`
   - `GROQ_API_KEY`
   - `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`
   - `JAAS_APP_ID`
   - `LI_CLIENT_ID`, `LI_CLIENT_SECRET`, `LI_REDIRECT_URI`, `LI_SCOPE`
   - `QR_JWT_SECRET_KEY`
3. Keep `DATABASE_MODE=aws`.

The active runtime uses AWS RDS through `AWS_DATABASE_URL`.

## Local setup

### Backend

```powershell
cd Backend
pip install -r requirements.txt
python seed_hr_user.py
```

This creates or updates:

- email: `rajkumar@hiresy.com`
- password: `123`

Start services in separate terminals:

```powershell
uvicorn services.main_api.app:app --host 0.0.0.0 --port 8000
uvicorn services.evaluator.app:app --host 0.0.0.0 --port 8001
uvicorn services.shortlisting_test.app:app --host 0.0.0.0 --port 8002
uvicorn services.coding_test.app:app --host 0.0.0.0 --port 8003
uvicorn services.live_hr.app:app --host 0.0.0.0 --port 8004
```

### Frontend

```powershell
cd Frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## Local validation checklist

- Log in with `rajkumar@hiresy.com / 123`
- Create a job with `MCQ Test` or `Aptitude Test`
- Apply as a candidate with resume and cover letter
- Open the public/manual test link
- Complete the QR 360 room scan before starting the test
- Trigger malpractice signals such as tab switch or permission denial
- Verify evidence appears in the HR candidate workflow
- Complete BGV, offer, approval, and onboarding flow

## Docker builds

Build the backend image from the `Backend` root:

```powershell
docker build -f Backend/Dockerfile Backend -t hiresy-backend
```

Build the frontend image from the `Frontend` root:

```powershell
docker build -f Frontend/Dockerfile Frontend -t hiresy-frontend
```

Example backend service run with a Railway-style command:

```powershell
docker run --rm -p 8000:8000 hiresy-backend sh -c "uvicorn services.main_api.app:app --host 0.0.0.0 --port 8000"
```

Example frontend run:

```powershell
docker run --rm -p 3000:3000 hiresy-frontend
```

## Ngrok testing

Run the local stack first, then expose the frontend:

```powershell
ngrok http 5173
```

Update `.env` if you want backend-generated links to be public:

- `PUBLIC_FRONTEND_URL=https://your-ngrok-domain`

Because Vite proxies `/api`, `/test-api`, `/coding-api`, and `/livehr-api`, one frontend tunnel is enough for candidate links during local testing.

## Interview configuration notes

- `Aptitude Test` is a real executable round and reuses the existing proctored MCQ engine.
- `Group Discussion` is display-only in the UI and stored in config, but it does not generate a backend session.
- `Technical HR` and `HR Interview` stay inside the locked final HR stage.

## Public repo hygiene

Before pushing publicly:

- confirm `.env` is not committed
- confirm AWS, SMTP, LinkedIn, GitHub, and Groq secrets are rotated if they were ever exposed
- remove local logs, caches, generated uploads, and test artifacts
- keep `.env.example` as the only tracked env template

## Push to GitHub

Typical flow:

```powershell
git status
git add .
git commit -m "Add Railway Docker deployment support"
git push -u origin main
```

## Render deployment

Deploy with a Render API key (`rnd_...` from **Account Settings → API Keys**).

### Quick API deploy (main-api + frontend)

```powershell
$env:RENDER_API_KEY = "rnd_your_key_here"
powershell -File scripts/render-deploy.ps1
```

This script:

- validates `render.yaml`
- fixes the existing backend Docker service (`hiresy-main-api`)
- creates `hiresy-frontend` as a static site if missing
- triggers deploys

### Full stack (Blueprint — 6 services)

1. Push `render.yaml` to GitHub.
2. In Render: **New → Blueprint** → connect `Rajkumar5723/JatayuS5-JustAgentic`.
3. Fill prompted secrets in the `hiresy-backend-shared` env group (from `.env.example`).
4. Set `LI_REDIRECT_URI` to `https://<hiresy-main-api-host>/linkedin/callback`.
5. After deploy, set `VITE_LIVEHR_WS_BASE` on the frontend to `wss://<hiresy-live-hr-host>/livehr/ws`.
6. Seed HR user once in a backend shell: `python seed_hr_user.py`.

| Service | Root | Start command |
|---|---|---|
| `hiresy-frontend` | `Frontend` | `npm ci && npm run build` (static) |
| `hiresy-main-api` | `Backend` | `uvicorn services.main_api.app:app` |
| `hiresy-evaluator` | `Backend` | `uvicorn services.evaluator.app:app` |
| `hiresy-shortlisting-test` | `Backend` | `uvicorn services.shortlisting_test.app:app` |
| `hiresy-coding-test` | `Backend` | `uvicorn services.coding_test.app:app` |
| `hiresy-live-hr` | `Backend` | `uvicorn services.live_hr.app:app` |

Workspace ID for API calls: `tea-d1nou1k9c44c73ejn8fg` (My Workspace).

## Railway Docker monorepo deployment

Deploy this as six Railway services from the same GitHub repo. Do not collapse the stack into one service.

### Service root directories

Use these exact root directories in Railway:

| Service | Root Directory |
|---|---|
| `frontend` | `Frontend` |
| `main-api` | `Backend` |
| `evaluator` | `Backend` |
| `shortlisting-test` | `Backend` |
| `coding-test` | `Backend` |
| `live-hr` | `Backend` |

Each service should use Dockerfile auto-detection:

- `Frontend/Dockerfile` for the frontend service
- `Backend/Dockerfile` for every backend service

Do not set a Custom Build Command. Railway should use the Dockerfile at the root of the selected deploy directory.

### Railway service names

Name the services exactly:

- `frontend`
- `main-api`
- `evaluator`
- `shortlisting-test`
- `coding-test`
- `live-hr`

These names matter because backend private-network URLs will use them.

### Backend start commands

Set a Custom Start Command on each backend service:

- `main-api`
  - `sh -c "uvicorn services.main_api.app:app --host 0.0.0.0 --port ${PORT}"`
- `evaluator`
  - `sh -c "uvicorn services.evaluator.app:app --host 0.0.0.0 --port ${PORT}"`
- `shortlisting-test`
  - `sh -c "uvicorn services.shortlisting_test.app:app --host 0.0.0.0 --port ${PORT}"`
- `coding-test`
  - `sh -c "uvicorn services.coding_test.app:app --host 0.0.0.0 --port ${PORT}"`
- `live-hr`
  - `sh -c "uvicorn services.live_hr.app:app --host 0.0.0.0 --port ${PORT}"`

Do not remove `sh -c`. Railway Docker start commands need a shell wrapper for `${PORT}` expansion.

Leave the frontend Custom Start Command empty and use the Docker `CMD`.

### Healthchecks

Configure these healthcheck paths:

| Service | Healthcheck |
|---|---|
| `frontend` | `/` |
| `main-api` | `/health` |
| `evaluator` | `/health` |
| `shortlisting-test` | `/health` |
| `coding-test` | `/health` |
| `live-hr` | `/health` |

### Backend variables

Set these on every backend service:

- `DATABASE_MODE=aws`
- `AWS_DATABASE_URL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_S3_BUCKET`
- `S3_EVIDENCE_BUCKET`
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `GROQ_MODEL_VISION`
- `GROQ_MODEL_AUDIO`
- `SMTP_USER`
- `SMTP_PASS`
- `SMTP_FROM`
- `JAAS_APP_ID`
- `LI_CLIENT_ID`
- `LI_CLIENT_SECRET`
- `LI_REDIRECT_URI`
- `LI_SCOPE`
- `QR_JWT_SECRET_KEY`
- `SHORTLIST_MIN_SCORE`

Set these public URL values on every backend service:

- `FRONTEND_URL=https://<frontend-domain>`
- `PUBLIC_FRONTEND_URL=https://<frontend-domain>`
- `PUBLIC_MAIN_API_URL=https://<main-api-domain>`

### Private networking values

Use Railway private networking for backend-to-backend communication:

- `MAIN_API_URL=http://main-api.railway.internal`
- `EVAL_API_URL=http://evaluator.railway.internal`
- `TEST_API_URL=http://shortlisting-test.railway.internal`
- `CODING_API_URL=http://coding-test.railway.internal`
- `LIVEHR_API_URL=http://live-hr.railway.internal`

### Frontend variables

Set these on the `frontend` service:

- `VITE_MAIN_API_BASE=https://<main-api-domain>`
- `VITE_TEST_API_BASE=https://<shortlisting-test-domain>`
- `VITE_CODING_API_BASE=https://<coding-test-domain>`
- `VITE_LIVEHR_API_BASE=https://<live-hr-domain>`
- `VITE_LIVEHR_WS_BASE=wss://<live-hr-domain>/livehr/ws`

The production frontend must use these public URLs. It must not rely on the Vite dev proxy.

### Watch paths

Use Watch Paths so unrelated changes do not rebuild every service:

- `main-api`
  - `Backend/core/**`
  - `Backend/services/main_api/**`
  - `Backend/requirements.txt`
- `evaluator`
  - `Backend/core/**`
  - `Backend/services/evaluator/**`
  - `Backend/requirements.txt`
- `shortlisting-test`
  - `Backend/core/**`
  - `Backend/services/shortlisting_test/**`
  - `Backend/requirements.txt`
- `coding-test`
  - `Backend/core/**`
  - `Backend/services/coding_test/**`
  - `Backend/requirements.txt`
- `live-hr`
  - `Backend/core/**`
  - `Backend/services/live_hr/**`
  - `Backend/requirements.txt`
- `frontend`
  - `Frontend/**`

### Railway deploy steps after push

1. Push the repo to GitHub.
2. In Railway, create or connect six services from the same repo.
3. Set the root directory for each service exactly as shown above.
4. Let Railway detect the Dockerfile from that root directory.
5. Configure each backend Custom Start Command.
6. Configure healthcheck paths.
7. Add backend shared secrets and URL variables.
8. Add frontend `VITE_*` variables.
9. Deploy all services.
10. Seed the default HR user once in a backend shell if your database is empty:

```powershell
python seed_hr_user.py
```

## Railway smoke checklist

- `main-api`, `evaluator`, `shortlisting-test`, `coding-test`, and `live-hr` return `200` on `/health`
- `frontend` returns `200` on `/`
- login works against AWS RDS
- candidate links use public Railway domains
- main API can reach internal backend services over `*.railway.internal`
- MCQ and Aptitude public links open correctly
- QR room scan gate blocks test start until complete
- coding and live HR routes open from public URLs
- S3-backed document preview and download works
- offer portal and signed PDF download work

## Known operational notes

- If a backend service name differs from this README, internal `*.railway.internal` URLs must be updated to match.
- If a backend Custom Start Command omits `sh -c`, `${PORT}` will not expand.
- If `VITE_*` variables are missing, the frontend falls back to local proxy paths and breaks in production.
- Free ngrok URLs change after restart, so refresh `PUBLIC_FRONTEND_URL` when needed during local testing.
- `Group Discussion` is intentionally UI-only and does not create a runnable test session.
