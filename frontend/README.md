# Frontend (React + Vite)

The base screen is **provided** — a payments feed + live loan balances. It fires
payments at the backend webhook and reflects the results; **"Simulate incoming
payment"** sends a new payment and **"Resend ↻"** re-fires an existing one (a rail
redelivery). You don't need to change it for the core task (the backend webhook).

As a **frontend extension**, build an **admin reconciliation & issues panel** on
top of this — see *Your task* in the root `README.md`.

```bash
npm install
npm run dev          # http://localhost:5137  (proxies the API to :8137)
```

The Vite dev server proxies API calls to the backend on `:8137`, so there's no
CORS to configure. Start the backend first (see the root `README.md`).
