# BLOGZENAI

BLOGZENAI is an AI-powered blog generation app with a FastAPI backend, Firebase-authenticated history, and a static frontend hosted from `public/`.

## Architecture

- `api.py`: FastAPI API surface for generation, auth-protected history, health checks, and anonymous free-generation enforcement.
- `main.py`: Orchestrates the multi-step blog workflow.
- `agents/`: Topic planning, research, writing, SEO, and export helpers.
- `utils/database.py`: Lazy Firestore access plus history and anonymous usage persistence.
- `public/`: Static HTML, CSS, and JavaScript for the content studio UI.

## Environment Variables

The API still supports explicit env vars, but local development can now bootstrap from the existing `bolgzenai` Firebase project plus Secret Manager if your Google auth is already set up.

Set these explicitly only if you want to override the defaults:

```env
NEWSDATA_API_KEY=your_newsdata_key
GCP_PROJECT=your_gcp_project_id
FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}
ANON_COOKIE_SECRET=replace_with_a_long_random_secret
ALLOWED_ORIGINS=https://bolgzenai.web.app,https://bolgzenai.firebaseapp.com,http://localhost:5500,http://127.0.0.1:5500
```

Notes:

- `ANON_COOKIE_SECRET` is required in production for the server-enforced anonymous free generation flow.
- `ALLOWED_ORIGINS` is optional. If omitted, the app falls back to the current production and local frontend origins.
- `FIREBASE_CREDENTIALS_JSON` must be valid JSON for a Firebase Admin service account.
- Local development falls back to the `bolgzenai` project in `.firebaserc`, loads secrets from Google Secret Manager, and derives a local-only cookie secret if a dedicated `ANON_COOKIE_SECRET` secret does not exist yet.
- On localhost, the anonymous free-generation cookie automatically switches to local-safe flags so you can test over plain HTTP.

## Local Setup

1. Create and activate a Python 3.11 virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Make sure your Google auth can access the `bolgzenai` project and Secret Manager.

4. Start the API:

```bash
uvicorn api:app --reload
```

5. Serve `public/` with any static file server if you want to test the frontend locally.

For a zero-env local run, the app will:

- resolve `GCP_PROJECT` from `.firebaserc`
- read `NEWSDATA_API_KEY` and `firebase-service-account-key` from Secret Manager
- initialize Firestore and Vertex AI with the fetched service-account credentials
- derive a local-only anonymous cookie secret when no dedicated `ANON_COOKIE_SECRET` secret exists yet

## API Overview

- `GET /health`: Basic health endpoint.
- `POST /generate-blog-free`: One anonymous generation per signed cookie, enforced by the backend.
- `POST /generate-blog`: Authenticated blog generation for signed-in users.
- `GET /history`: Authenticated history list for the current user.
- `GET /history/{history_id}`: Authenticated access to a single history item.

## Security and Hardening Notes

- Anonymous free-generation usage is tracked server-side in Firestore and tied to a signed cookie.
- Generated markdown is sanitized in the frontend before insertion into the DOM.
- Request validation now rejects blank, too-short, or oversized topics and unsupported tones.
- Blocking model-generation steps are moved off the async request path to keep FastAPI responsive under concurrent traffic.

## Deployment

This project includes:

- `Dockerfile` for containerized API deployment.
- `cloudbuild.yaml` for Google Cloud Build.
- `firebase.json` for Firebase Hosting of the static frontend.
