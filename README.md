# CreditHub — Engineering Take-Home: Loan Repayment & Early Settlement

Welcome, and thanks for taking the time. This is a small, self-contained slice
of a lending platform (FastAPI + SQLAlchemy). It mirrors how our real system is
built — including the patterns you'll extend and one or two things you might
disagree with.

**Timebox:** ~1–2 days. Ship what you'd be comfortable putting in front of a
bank, and be explicit about anything you'd do differently with more time.

**Use AI freely.** We build AI-first — Claude, Copilot, Cursor, whatever you
use. We're not testing whether you can write code without help; we're testing
your judgment about the code that comes out. (See `NOTES.md` below.)

---

## Setup (zero infra — SQLite)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m app.seed                 # create + seed the database
uvicorn app.main:app --reload      # http://localhost:8000/docs

pytest                             # provided tests: loans pass, repayments fail (your task)
```

## What's here

- `app/models.py` — `Loan`, `Repayment`, `AuditLog`. **Loans exist; repayment is not built.**
- `app/loans.py` — read endpoints (provided, working).
- `app/repayments.py` — **stubs you replace.** This is your task.
- `app/audit.py` — audit helper. Every mutation must leave an audit record.
- `app/auth.py` — role gate; pass a role via the `X-Role` header (`system`, `manager`, `admin`, `analyst`, `customer`).
- `tests/` — `test_loans.py` passes; `test_repayments.py` is a behaviour spec that currently **fails** against the stub.

---

## Your task

Build production-quality loan repayment and early settlement.

### Core (required)
1. **`POST /loans/{id}/repayments`** — record a repayment. Correctly handle
   **partial**, **exact**, and **overpayment**; reduce the outstanding balance;
   transition the loan to `paid_off` when fully repaid.
2. **Idempotency** — the same repayment submitted twice (a client/network
   retry) must not be applied twice.
3. **Audit** — every repayment writes an audit record, atomically with the
   payment (no orphan record if the payment fails).
4. **AuthZ** — only appropriate role(s) may post repayments; reject the rest.
5. **State** — you cannot repay a `cancelled` / `written_off` / `paid_off` loan.
6. **Tests** — make the provided spec pass and add your own that would actually
   catch a regression.

### Extension (expected in a strong submission)
7. **`GET /loans/{id}/settlement-quote`** — compute an early full-settlement
   amount and allow it to be paid to close the loan.

### Optional stretch (only if you have time — don't force it)
8. Make repayment correct under two **simultaneous** requests on the same loan.

---

## What to hand back

1. Your code (a branch/PR-style diff is ideal).
2. **`NOTES.md`** — short. Cover:
   - Key design decisions and any edge cases you handled.
   - **Anything you'd flag before this ships to a real lender.**
   - **How you used AI** on this — where it helped, and anywhere you overrode
     or corrected it.

We'll follow up with a ~30-minute call where you walk us through your own code.

Have fun — and tell us what you'd change about *our* setup, too.
