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

The app runs as a multi-service stack:

- `Frontend` on port `5173`
- `main-api` on port `8000`
- `evaluator` on port `8001`
- `shortlisting-test` on port `8002`
- `coding-test` on port `8003`
- `live-hr` on port `8004`

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL on AWS RDS
- AWS S3 bucket for documents and evidence
- Redis if you use the configured Celery URLs
- Tesseract OCR installed if you want scanned-image OCR locally

## Environment setup

1. Copy `.env.example` to `.env`.
2. Fill in:
   - `AWS_DATABASE_URL`
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_S3_BUCKET`
   - `S3_EVIDENCE_BUCKET`
   - `GROQ_API_KEY`
   - `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`
   - `JAAS_APP_ID`
3. Keep `DATABASE_MODE=aws`.

The active runtime uses AWS RDS through `AWS_DATABASE_URL`.

## Local setup

### Backend

Install Python dependencies:

```powershell
cd Backend
pip install -r requirements.txt
```

Seed the default HR user:

```powershell
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
- confirm AWS, SMTP, LinkedIn, and GitHub secrets are rotated if they were ever exposed
- remove local logs, caches, generated uploads, and test artifacts
- keep `.env.example` as the only tracked env template

## Push to GitHub

If the repo is already initialized, use the existing repo instead of re-running `git init`.

Typical flow:

```powershell
git status
git add .
git commit -m "Prepare AWS-only public release"
git remote set-url origin https://github.com/Rajkumar5723/JatayuS5-JustAgentic.git
git push -u origin main
```

## Railway deployment after GitHub push

Deploy this as multiple Railway services, not as a single merged backend.

### 1. Create projects/services

Create six Railway services from the same GitHub repo:

- `frontend`
- `main-api`
- `evaluator`
- `shortlisting-test`
- `coding-test`
- `live-hr`

### 2. Configure service start commands

Use these start commands:

- `main-api`: `uvicorn services.main_api.app:app --host 0.0.0.0 --port $PORT`
- `evaluator`: `uvicorn services.evaluator.app:app --host 0.0.0.0 --port $PORT`
- `shortlisting-test`: `uvicorn services.shortlisting_test.app:app --host 0.0.0.0 --port $PORT`
- `coding-test`: `uvicorn services.coding_test.app:app --host 0.0.0.0 --port $PORT`
- `live-hr`: `uvicorn services.live_hr.app:app --host 0.0.0.0 --port $PORT`
- `frontend`: build with Vite and serve the generated assets with your chosen static host pattern

### 3. Set backend env vars on every backend service

- `DATABASE_MODE=aws`
- `AWS_DATABASE_URL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_S3_BUCKET`
- `S3_EVIDENCE_BUCKET`
- `GROQ_API_KEY`
- `SMTP_USER`
- `SMTP_PASS`
- `SMTP_FROM`
- `JAAS_APP_ID`
- `SHORTLIST_MIN_SCORE`

Also set service-to-service URLs:

- `MAIN_API_URL=https://<main-api-domain>`
- `EVAL_API_URL=https://<evaluator-domain>`
- `TEST_API_URL=https://<shortlisting-domain>`
- `CODING_API_URL=https://<coding-domain>`
- `LIVEHR_API_URL=https://<live-hr-domain>`

Set:

- `PUBLIC_FRONTEND_URL=https://<frontend-domain>`
- `PUBLIC_MAIN_API_URL=https://<main-api-domain>`

### 4. Set frontend env vars

- `VITE_MAIN_API_BASE=https://<main-api-domain>`
- `VITE_TEST_API_BASE=https://<shortlisting-domain>`
- `VITE_CODING_API_BASE=https://<coding-domain>`
- `VITE_LIVEHR_API_BASE=https://<live-hr-domain>`
- `VITE_LIVEHR_WS_BASE=wss://<live-hr-domain>/livehr/ws`

### 5. Final Railway checks

- login works against AWS RDS
- candidate links open from public Railway domains
- S3 document previews/downloads work
- QR room scan and test gating work over public HTTPS
- offer portal and signed PDF download work

## Known operational notes

- If scanned-document OCR is required locally, install Tesseract first.
- Free ngrok URLs change after restart, so refresh `PUBLIC_FRONTEND_URL` when needed.
- `Group Discussion` is intentionally UI-only and will not create a runnable test session.
