# CreditHub — Engineering Take-Home: Loan Repayment (Full-Stack)

Welcome, and thanks for taking the time. This is a small, self-contained slice
of a lending platform — a **FastAPI + SQLAlchemy** backend and a **React + Vite**
frontend. It mirrors how our real system is built, including the patterns you'll
extend and one or two things you might disagree with.

**Timebox:** ~1–2 days. Ship what you'd be comfortable putting in front of a
bank, and be explicit about anything you'd do differently with more time.

**Use AI freely.** We build AI-first — Claude, Copilot, Cursor, whatever you
use. We're not testing whether you can write code without help; we're testing
your judgment about the code that comes out. (See `NOTES.md` below.)

---

## Run it locally

You need **Python 3.11+** and **Node 18+**.

**One command** (seeds the DB, starts API on `:8137`, frontend on `:5137`):
```bash
./run-local.sh          # then open http://localhost:5137
```

**Or two terminals:**
```bash
# terminal 1 — backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --port 8137     # http://localhost:8137/docs

# terminal 2 — frontend
cd frontend
npm install
npm run dev                                    # http://localhost:5137
```

*(Non-standard ports on purpose — 8000/5173 often clash with other projects. The
frontend proxies to :8137, so keep the API on that port.)*

**Tests (backend):**
```bash
pytest                  # loans pass; repayments fail — that's your task
```

## What's here

**Backend** (`app/`)
- `models.py` — `Loan`, `Repayment`, `AuditLog`. Loans exist; **repayment is not built**.
- `loans.py` — read endpoints (provided, working).
- `repayments.py` — **stubs you replace.**
- `audit.py` — audit helper. Every mutation must leave an audit record.
- `auth.py` — role gate via the `X-Role` header (`system`, `manager`, `admin`, `analyst`, `customer`).
- `tests/` — `test_loans.py` passes; `test_repayments.py` is a behaviour spec that currently **fails**.

**Frontend** (`frontend/`)
- React + Vite. Lists loans out of the box (proxied to the API). **The repayment UI is your task** — see the TODOs in `src/App.jsx`.

---

## Your task

Build production-quality loan repayment, backend **and** frontend.

### Backend — core (required)
1. **`POST /loans/{id}/repayments`** — record a repayment. Handle **partial**,
   **exact**, and **overpayment**; reduce the outstanding balance; transition the
   loan to `paid_off` when fully repaid.
2. **Idempotency** — the same repayment submitted twice (a retry) must not apply twice.
3. **Audit** — every repayment writes an audit record, atomically with the payment.
4. **AuthZ** — only appropriate role(s) may post repayments; reject the rest.
5. **State** — you cannot repay a `cancelled` / `written_off` / `paid_off` loan.
6. **Tests** — make the provided spec pass and add your own.

### Frontend — required
7. A small UI to **make a repayment**: pick a loan, enter an amount, submit,
   show the result and the **updated balance**, and handle the API's error cases
   (403 / 409 / 422) with a readable message. Keep it small — we're looking at how
   you wire state, calls, and error handling, not at visual polish.

### Extension (expected in a strong submission)
8. **`GET /loans/{id}/settlement-quote`** — compute an early full-settlement
   amount and allow it to be paid to close the loan (surface it in the UI).

### Optional stretch (only if you have time)
9. Make repayment correct under two **simultaneous** requests on the same loan.

---

## What to hand back

1. Your code (a branch/PR-style diff is ideal).
2. **`NOTES.md`** — short. Cover:
   - Key design decisions and edge cases you handled.
   - **Anything you'd flag before this ships to a real lender.**
   - **How you used AI** — where it helped, and anywhere you overrode it.

We'll follow up with a ~30-minute call where you walk us through your own code.

Have fun — and tell us what you'd change about *our* setup, too.
