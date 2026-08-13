# CreditHub — Engineering Take-Home: Payment Reconciliation (Full-Stack)

Welcome, and thanks for taking the time. This is a small, self-contained slice
of a lending platform — a **FastAPI + SQLAlchemy** backend and a **React + Vite**
frontend.

In the real world, loan repayments aren't typed in by hand — they **arrive from
rails** (payment gateways, NIBSS GSI, core-banking postings) as events, and the
platform **reconciles** each one against a loan. This exercise models exactly
that: a payment lands (we simulate it), and your job is to **reconcile it — "tick
it off" against the loan — and reflect it in the UI.**

**Timebox:** ~1–2 days. Ship what you'd be comfortable putting in front of a
bank, and be explicit about anything you'd do differently with more time.

**Use AI freely.** We build AI-first — Claude, Copilot, Cursor, whatever you use.
We're not testing whether you can code without help; we're testing your judgment
about the code that comes out. (See `NOTES.md`.)

---

## Run it locally

Needs **Python 3.11+** and **Node 20.19+**.

```bash
./run-local.sh          # seeds the DB, API on :8137, frontend on :5137 → open http://localhost:5137
```
Or two terminals — see the commands at the bottom. Tests: `pytest`.

*(Non-standard ports on purpose — 8000/5173 often clash with other projects. The
frontend proxies to :8137, so keep the API on that port.)*

## The loop

1. A payment lands → a `PaymentEvent` row in **`pending`** status (we provide a
   **"Simulate incoming payment"** button — a fake gateway callback).
2. **You reconcile it:** match it to its loan, apply the money, and **tick the
   event off** (`pending → applied`).
3. The UI reflects the new balance and the event's status.

## What's here

**Backend** (`app/`)
- `models.py` — `Loan`, `PaymentEvent`, `Repayment`, `AuditLog`.
- `loans.py` — read endpoints (provided).
- `payments.py` — **provided:** `GET /payment-events` (the feed) and
  `POST /simulate/payment` (drop a pending event). **Your task:** the
  `POST /payment-events/{id}/apply` stub.
- `audit.py` — audit helper (writes into the caller's transaction).
- `auth.py` — role gate via the `X-Role` header.
- `tests/` — `test_loans.py` + the feed/simulate tests pass; the reconciliation
  spec in `test_payments.py` **fails** against the stub.

**Frontend** (`frontend/`)
- React + Vite. Loans table, payments feed, and the Simulate button all work.
  Wiring **Apply** (reconcile) is your task — see the TODO in `src/App.jsx`.

---

## Your task

### Backend — `POST /payment-events/{id}/apply` (required)
Reconcile one pending payment. Contract:

- **`403`** if the caller's role may not reconcile; **`404`** if the event doesn't exist.
- **Apply** a valid pending event: record a `Repayment`, reduce the loan's
  outstanding, **close the loan** (`paid_off`) when fully repaid, set the event to
  **`applied`** with `processed_at`, and write an **audit** record — all in **one
  transaction**. Return `200 {event, loan}`.
- **Idempotent:** applying an already-applied event does **not** apply it again.
- **Reject** (set the event to `rejected` with a `reason`, return `200`) when it
  can't be applied — the loan isn't `active`, or the payment is a **duplicate**
  (its `external_ref` was already applied — rails redeliver).
- Decide and document how you treat **overpayment**.

### Frontend — required
Wire the **Apply** button so reconciling a payment updates the loan balance and
the event status on screen, and surface the `403 / 404` cases with a readable
message. Match the bar of the rest of the UI.

### Extension (expected in a strong submission)
A **"Reconcile all pending"** action (batch), or auto-reconcile on receipt.

### Optional stretch (only if you have time)
Make reconciliation correct under **concurrent** applies of the same event / loan.

---

## What to hand back

1. Your code (a branch/PR-style diff is ideal).
2. **`NOTES.md`** — short: key decisions + edge cases; **anything you'd flag
   before this ships to a real lender**; and **how you used AI** (where it helped,
   where you overrode it).

We'll follow up with a ~30-minute call where you walk us through your own code.

---

<details><summary>Two-terminal run</summary>

```bash
# terminal 1 — backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --port 8137     # http://localhost:8137/docs

# terminal 2 — frontend
cd frontend && npm install && npm run dev      # http://localhost:5137
```
</details>
