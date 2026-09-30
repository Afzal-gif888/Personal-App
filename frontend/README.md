# Frontend

Owns the React, TypeScript, UI, routing, client state and the API/service layer (`src/services`). All data comes from the backend; there is no mock data. The application was moved here without changing its behavior.

## Run independently

```powershell
npm ci
npm run dev
```

Other available commands: `npm run build`, `npm run lint`, and `npm run preview`.

Services call the backend at `/api/v1` (proxied to `http://localhost:8000` in development; set `VITE_API_URL` for another origin).

## Deploy (Vercel)

Self-contained: deploy this folder with **Root Directory = `frontend`**. `vercel.json` sets the build (`npm ci`, `npm run build` → `dist`), sends every page URL to `index.html`, caches `/assets` for a year and adds security headers. The only setting is `VITE_API_URL` = the backend's public URL (see `.env.example`); it is built in, so redeploy after changing it. Step by step: [../DEPLOY.md](../DEPLOY.md).
