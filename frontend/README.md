# Frontend

Owns the existing React, TypeScript, UI, routing, state, API/service layer, and mock data. The application was moved here without changing its behavior.

## Run independently

```powershell
npm ci
npm run dev
```

Other available commands: `npm run build`, `npm run lint`, and `npm run preview`.

The current application uses mock services. When the backend is available, configure a public `VITE_API_BASE_URL` and replace/adapt service implementations to the versioned REST contract. Never place LLM keys, database credentials, or other secrets in frontend variables; Vite embeds `VITE_*` values in browser assets.
