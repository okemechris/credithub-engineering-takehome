# Frontend (React + Vite)

Small UI on top of the loan-servicing API. The loan list is provided and works
once the backend is running; the **repayment UI is your task** (see the TODOs in
`src/App.jsx`).

```bash
npm install
npm run dev          # http://localhost:5173  (proxies /loans, /health to :8000)
```

The Vite dev server proxies API calls to the backend on `:8000`, so there's no
CORS to configure. Start the backend first (see the root `README.md`).
