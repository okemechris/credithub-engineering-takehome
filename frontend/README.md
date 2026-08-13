# Frontend (React + Vite)

This screen is **entirely provided** — you don't have to change it (polish it if
you like). It fires payments at the backend webhook and shows the feed + live
loan balances. Once you build `POST /webhooks/payments`, **"Simulate incoming
payment"** shows payments getting applied/rejected and the balances updating;
**"Resend ↻"** re-fires an existing payment (a rail redelivery).

```bash
npm install
npm run dev          # http://localhost:5137  (proxies the API to :8137)
```

The Vite dev server proxies API calls to the backend on `:8137`, so there's no
CORS to configure. Start the backend first (see the root `README.md`).
