# Deploying It's Personal

**Vercel** (frontend) · **Railway** (backend + Agent Core) · **Neon** (PostgreSQL + pgvector)

```
Browser ──► Vercel (React app)
   │
   └──── API calls ──► Railway: backend (public URL, /data volume for uploads, reminder scheduler)
                          │   ▲
          private network │   │ private network (user's own token)
                          ▼   │
                       Railway: agent-core (no public URL) ──► Gemini
                          │
   backend ──► Neon (PostgreSQL + pgvector) · EmailJS · Gemini embeddings
```

The deployment files are already in the repo:

| File | What it does |
| --- | --- |
| `backend/Dockerfile`, `backend/docker-entrypoint.sh` | Builds the API. On every start it applies database migrations, prepares the uploads volume, then runs as a non-root user |
| `backend/railway.json`, `agent-core/railway.json` | Railway build and health-check settings (one replica each) |
| `agent-core/Dockerfile` | Builds the Agent Core |
| `frontend/vercel.json` | Vercel build, page routing and caching |
| `frontend/.env.example` | The one frontend setting: `VITE_API_URL` |

Both images were built and tested locally in production mode. The test ran migrations on an empty database (including pgvector), reached Agent Core over a private network, checked CORS, and confirmed uploads survive a redeploy.

---

## 0. Before you start

1. Push the project to a **GitHub** repository (private is fine). Commit everything, including the new files above. `.env` files are git-ignored, so keys never leave your PC.
2. Create accounts on [neon.tech](https://neon.tech), [railway.com](https://railway.com) and [vercel.com](https://vercel.com). Sign in with GitHub on all three.
3. Generate three secrets and keep them somewhere safe:
   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"   # run 3 times: JWT_SECRET, JWT_REFRESH_SECRET, AGENT_CORE_SERVICE_TOKEN
   ```

## 1. Database: Neon

1. **Create project**. Pick the region closest to your students (e.g. *AWS Asia Pacific (Mumbai)* for India) and the newest PostgreSQL version offered.
2. Open **Connect** and turn **Connection pooling off**, so you get the *direct* connection string (the host has no `-pooler`). The app keeps its own connection pool, and the pooled endpoint can break its prepared statements.
3. Copy the string. It looks like:
   `postgresql://neondb_owner:••••@ep-xxxx.ap-south-1.aws.neon.tech/neondb?sslmode=require`

Nothing else to do: the first backend start creates all tables and enables `pgvector`.

## 2. Backend + Agent Core: Railway

### 2a. Backend service

1. **New Project → Deploy from GitHub repo →** pick your repo.
2. Open the service. In **Settings**:
   - Rename it to `backend` (this becomes its private address `backend.railway.internal`).
   - Set **Root Directory** to `/backend`. If Railway doesn't pick up the config automatically, set **Config-as-code path** to `/backend/railway.json`.
3. Open the service's menu, choose **Attach volume** (or **+ Volume**), and set the **mount path** to `/data`. Uploaded documents live here.
4. In **Variables**, use the **Raw Editor** and paste this, filling in your values:
   ```env
   APP_ENV=production
   LOG_LEVEL=INFO
   PORT=8000
   DATABASE_URL=<Neon direct connection string>
   JWT_SECRET=<secret 1>
   JWT_REFRESH_SECRET=<secret 2>

   AGENT_CORE_MODE=agent
   AGENT_CORE_URL=http://agent-core.railway.internal:8001
   AGENT_CORE_SERVICE_TOKEN=<secret 3>

   # Set after step 3, when you know the Vercel address:
   CORS_ORIGINS=https://<your-app>.vercel.app
   APP_BASE_URL=https://<your-app>.vercel.app

   STORAGE_PATH=/data/storage
   SCHEDULER_ENABLED=true

   EMAILJS_SERVICE_ID=<from backend/.env>
   EMAILJS_TEMPLATE_ID=<from backend/.env>
   EMAILJS_NOTIFICATION_TEMPLATE_ID=<from backend/.env>
   EMAILJS_PUBLIC_KEY=<from backend/.env>
   EMAILJS_PRIVATE_KEY=<from backend/.env>

   EMBEDDING_PROVIDER=gemini
   EMBEDDING_API_KEY=<your Gemini key>
   EMBEDDING_MODEL=gemini-embedding-2
   EMBEDDING_DIMENSIONS=768
   DOCUMENT_SEARCH_TOP_K=5
   DOCUMENT_SEARCH_MIN_SIMILARITY=0.65
   ```
5. In **Settings → Networking**, choose **Generate Domain**. You get something like `backend-production-xxxx.up.railway.app`. Open `https://…/health`; it should show `{"status":"ok"}`.

### 2b. Agent Core service

1. In the same project, choose **+ Create → GitHub Repo →** the same repo.
2. In **Settings**, rename the service to `agent-core` and set **Root Directory** to `/agent-core` (config path `/agent-core/railway.json` if needed). **Don't** generate a public domain: only the backend talks to it.
3. **Variables**:
   ```env
   APP_ENV=production
   LOG_LEVEL=INFO
   PORT=8001
   AGENT_CORE_SERVICE_TOKEN=<secret 3, the same as the backend's>
   BACKEND_API_URL=http://backend.railway.internal:8000

   LLM_PROVIDER=gemini
   LLM_API_KEY=<your Gemini key>
   MUTATION_POLICY=approval
   LLM_PLANNING=false
   # Shared by ALL students. Raise to what your Gemini plan allows (45/day is only enough for one person).
   LLM_MAX_REQUESTS_PER_MINUTE=15
   LLM_MAX_REQUESTS_PER_DAY=500
   ```

Keep **one replica** for each service (already set in `railway.json`). The backend runs the reminder scheduler, and it must run exactly once.

## 3. Frontend: Vercel

1. **Add New → Project →** import the repo.
2. Set **Root Directory** to `frontend` (Vercel detects Vite; the rest comes from `vercel.json`).
3. Under **Environment Variables**, add `VITE_API_URL` = `https://backend-production-xxxx.up.railway.app` (your backend domain, no trailing slash).
4. Click **Deploy**. You get `https://<your-app>.vercel.app`.
5. Go back to Railway → backend → Variables. Set `CORS_ORIGINS` and `APP_BASE_URL` to that exact Vercel URL. The backend redeploys automatically.

`VITE_API_URL` is read at build time. If the backend address ever changes, redeploy the frontend in Vercel.

## 4. Check it works

1. `https://<backend>/health` shows `{"status":"ok"}`.
2. Open the Vercel URL. **Register**, then **Sign in**; the 6-digit code arrives by email.
3. **Assistant**: ask "What's due this week?" You should get a reply (this proves Agent Core and Gemini work).
4. **Documents**: upload a PDF. It should show **Searchable** after a few seconds. Then ask the assistant about it.
5. **Reminders**: create one for 2 minutes from now. The email arrives within about a minute of that time.
6. On your phone: open the Vercel URL. It works anywhere, not just on your Wi-Fi.

## 5. Updating the app

`git push` to the main branch. Vercel and Railway rebuild automatically, and the backend applies any new migrations on start. Uploaded files (on the `/data` volume) and the database (on Neon) are kept.

## 6. Optional: copy your local data to Neon

A fresh start is simplest. To move your existing accounts, reminders and chats instead, do this **before** the first backend deploy. Run it from the project root with Docker running:

```powershell
docker exec agentos-db pg_dump -U agentos -d agentos --no-owner --no-privileges -f /tmp/agentos.sql
docker cp agentos-db:/tmp/agentos.sql .\agentos.sql
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" "<Neon direct connection string>" -f .\agentos.sql
Remove-Item .\agentos.sql      # it contains your data: don't commit it
```
(It goes through a file because piping a dump through Windows PowerShell can corrupt its encoding.)

Uploaded files stay on your PC (`backend/storage`), so re-upload documents after moving. To re-index everything with fresh embeddings, use **Retry indexing**.

## 7. Costs and limits (check each provider's current pricing)

| Service | Expect |
| --- | --- |
| Vercel | Free (Hobby plan) |
| Neon | Free tier: enough storage for thousands of students' notes to start |
| Railway | Usage-based. Two small always-on services plus a small volume come to roughly $5–10/month |
| Gemini | Free-tier quotas are per minute and per day, shared by all students. Upgrade the plan if chats start failing |
| EmailJS | The free plan's ~200 emails/month runs out quickly (every login sends a code). Move to a paid plan for real use |

## 8. Troubleshooting

| Symptom | Fix |
| --- | --- |
| Frontend shows "Can't reach the server" | `VITE_API_URL` is wrong or missing. Fix it in Vercel and **redeploy** |
| Browser console shows a CORS error | `CORS_ORIGINS` on the backend must contain the address shown in the browser's error ("from origin …"). The backend's startup log line `CORS allowed origins` shows what it applied. Vercel gives every deploy a new `…-<hash>-…vercel.app` URL: use the stable project domain from Vercel → Settings → Domains, or set `CORS_ORIGIN_REGEX` |
| Backend crashes on start: `JWT_SECRET … must be set in production` | Set `JWT_SECRET` and `JWT_REFRESH_SECRET` |
| Backend log: migration error mentioning `vector` | `DATABASE_URL` isn't Neon, or isn't the direct connection. Use Neon's direct string |
| Assistant replies that it isn't set up | Agent Core isn't reachable. Check both services' `AGENT_CORE_SERVICE_TOKEN` match, and that the backend's `AGENT_CORE_URL` is `http://agent-core.railway.internal:8001` |
| Uploaded documents disappear after a deploy | The volume isn't mounted at `/data`, or `STORAGE_PATH` isn't `/data/storage` |
| No login code email | Check `EMAILJS_*` values. In EmailJS → Account → Security, API access for non-browser apps must stay enabled |
| Links in emails point to localhost | Set `APP_BASE_URL` to the Vercel URL |
