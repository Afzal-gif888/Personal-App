# Frontend

Owns the React, TypeScript, UI, routing, client state and the API/service layer (`src/services`). All data comes from the backend; there is no mock data. The application was moved here without changing its behavior.

## Run independently

```powershell
npm ci
npm run dev
```

Other available commands: `npm run build`, `npm run lint`, and `npm run preview`.

Services call the backend at `/api/v1` (proxied to `http://localhost:8000` in development; set `VITE_API_URL` for another origin).
