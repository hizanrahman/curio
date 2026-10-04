# Deployment: Vercel (frontend) + Render (backend)

The repo deploys as two services:

| Service | Provider | Config | Entry |
|---|---|---|---|
| Frontend SPA (React/Vite) | Vercel | [frontend/vercel.json](frontend/vercel.json) | `dist/` after `npm run build` |
| Backend API (FastAPI) | Render | [render.yaml](render.yaml) (Blueprint) | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |

Both deploy from the same Git repository. `.env` files are gitignored — all secrets are
provided through the dashboards.

## 0. Prerequisites

- A Git repository on GitHub/GitLab containing this project.
- Render account + Vercel account connected to that repo.
- Supabase project with migrations applied (run the SQL files in
  `supabase/migrations/` in numeric order via the Supabase SQL editor).

## 1. Backend on Render (do this first — the frontend needs its URL)

1. Render dashboard → **New → Blueprint** → pick the repository.
   Render reads [render.yaml](render.yaml) and creates the `curio-api` web service
   (Python 3.12, free plan, health check on `/`).
2. Fill in the secrets marked `sync: false` in `render.yaml`:

   | Env var | Value |
   |---|---|
   | `OPENAI_API_KEY` | your bazaarlink API key |
   | `SUPABASE_URL` | `https://<project>.supabase.co` |
   | `SUPABASE_ANON_KEY` | Supabase → Settings → API → anon/public key |
   | `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Settings → API → service_role key |
   | `API_ALLOWED_ORIGINS` | your Vercel URL, e.g. `https://curio.vercel.app` (comma-separated for multiple) |

   The rest are pre-filled by the blueprint:
   `OPENAI_BASE_URL=https://api.bazaarlink.ai/v1`, `OPENAI_MODEL=qwen/qwen3.7-flash:free`,
   `OPENAI_VISION_MODEL=qwen/qwen3.7-flash:free`, `PYTHON_VERSION=3.12.8`.

3. Deploy. Verify: `curl https://<service>.onrender.com/` → `{"status":"ok"}`.

> **CORS is strict by design:** requests from origins not listed in
> `API_ALLOWED_ORIGINS` get HTTP 400 on preflight. If the frontend later moves to a new
> domain, update this var and restart the service.

## 2. Frontend on Vercel

1. Vercel dashboard → **Add New → Project** → import the repository.
2. Set **Root Directory** to `frontend` (Settings → General). This is required —
   the app lives in a subfolder of the repo.
3. Framework preset: Vite (auto-detected). Build command/output come from
   [frontend/vercel.json](frontend/vercel.json): `npm run build` → `dist`.
4. Add environment variables (Environment: Production/Preview/Development):

   | Env var | Value |
   |---|---|
   | `VITE_API_URL` | the Render URL from step 1, e.g. `https://curio-api.onrender.com` |
   | `VITE_SUPABASE_URL` | `https://<project>.supabase.co` |
   | `VITE_SUPABASE_ANON_KEY` | Supabase anon/public key |

   These are **baked in at build time** — changing them later requires a redeploy.
5. Deploy. The SPA rewrite in `vercel.json` handles React Router deep links
   (`/session/:id` refreshes must not 404).

## 3. Supabase auth URLs

Supabase → Authentication → URL Configuration → add `https://<your-vercel-domain>`
to **Site URL** and **Redirect URLs**, or sign-in redirects will be blocked.

## 4. Post-deploy smoke test

```bash
# backend health
curl https://<service>.onrender.com/                     # {"status":"ok"}
curl https://<service>.onrender.com/api/problems/test    # {"status":"reloaded"}

# CORS: must return access-control-allow-origin for your Vercel origin
curl -si -X OPTIONS https://<service>.onrender.com/api/sessions \
  -H "Origin: https://<your-vercel-domain>" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: authorization,content-type" | head -5
```

Then in the browser: sign in → start a problem on `/learn` → confirm the tutor replies
and the learning map renders on the session page.

## Notes

- **Render free plan** spins the service down after inactivity; the first request after
  idle takes ~30–60s (cold start).
- `render.yaml` blueprint changes re-apply on Git sync; env secrets set in the dashboard
  are preserved.
- Frontend env changes need a Vercel **redeploy**; backend env changes need a Render
  **restart**.
