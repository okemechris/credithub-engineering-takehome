# Frontend (React + Vite)

Small UI on top of the servicing API. The loans table, the payments feed, and
the **"Simulate incoming payment"** button all work once the backend is running;
**wiring the Apply (reconcile) action is your task** — see the TODOs in
`src/App.jsx`.

```bash
npm install
npm run dev          # http://localhost:5137  (proxies the API to :8137)
```

The Vite dev server proxies API calls to the backend on `:8137`, so there's no
CORS to configure. Start the backend first (see the root `README.md`).
