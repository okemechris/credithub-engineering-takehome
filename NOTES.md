# Notes

## Key decisions

**Overpayment rejects instead of cap-and-credit.** A payment bigger than the
outstanding balance gets bounced (`reason_code: overpayment`), loan untouched.
Real lenders often cap it and carry the excess as a credit, but that needs a
suspense-account model this schema doesn't have. Reject-and-route-to-ops is
the right scope here. It's the first thing I'd revisit before this goes near
a real lender, since it's a bad borrower experience at volume.

**Reconciliation is one transaction.** `receive_payment` writes the
`PaymentEvent`, decides apply/reject, and on apply updates the loan + writes
the audit row, all before one `db.commit()`. Rollback discards the whole
attempt so nothing can disagree.

**Duplicate `external_ref` rejects rather than re-applying.** Checked against
any existing `applied` event with the same ref.

**Concurrency.** Two webhooks racing on the same loan/`external_ref` is the
main risk. Everything gets recorded either way, but only one should ever
move the balance. `_lock_loan` uses `SELECT ... FOR UPDATE`, which is the
right call on a real DB but a silent no-op on SQLite (what this app actually
runs on). SQLite also only opens a real transaction on the first *write*, so
two threads can both pass the "not yet applied" check before either grabs the
lock. Fixed with `serialized_write()` in `db.py`, which forces `BEGIN
IMMEDIATE` on the webhook's transaction so the second request genuinely
blocks and re-reads fresh state. Scoped to just the webhook via a
`ContextVar` (not `threading.local()`: FastAPI's sync routes happen to run
one-thread-per-request, but that's not a guarantee, and `async def` routes
wouldn't preserve it) so plain GETs don't fight for that lock. Also switched
SQLite to WAL mode so reads aren't blocked for the webhook's whole write, and
bumped busy-timeout 5s → 30s for bursts queuing on the lock. Guarded on
`_is_sqlite` since `BEGIN IMMEDIATE` is SQLite-only syntax.

Dropped a partial unique index I'd tried earlier as a DB-level backstop,
wrong tool, since it rejects the *insert* and we need to store duplicates,
just not apply them.

Response is built from the in-memory objects before `db.commit()`, not
after. `expire_on_commit` would otherwise force a fresh SELECT once the lock
is released, which could read a different request's commit.

Tested with 10 concurrent threads POSTing the same `external_ref`: exactly
one `applied`, nine `rejected`, balance moves once, all 10 events stored
(`test_concurrent_redeliveries_apply_exactly_once`). The duplicate check
can't protect a *different* race though: two distinct, legitimate payments
racing on the same loan, each with its own `external_ref`, together
overpaying it. Same `serialized_write()` lock covers that too, since a
second thread only reads the balance after the first has committed, not off
a stale pre-race snapshot. Tested with 10 threads each paying 20000 against
a 56000 balance: exactly 2 apply (the most that fit), 8 reject as
overpayment, balance never goes negative
(`test_concurrent_different_payments_never_overdraw_the_loan`).

The lock is held for the whole request, which is fine only because nothing
in the critical section makes a network call. It's local DB work,
microseconds. If a real rail confirmation call ever gets added here, do that
*before* taking the lock, not inside it.

**Auth is a real HMAC signature (`X-Webhook-Signature`), not a shared
token.** `require_webhook_signature` in `auth.py` recomputes HMAC-SHA512 over
the raw body and compares in constant time, mirroring Paystack's convention.
Signing the raw bytes (not the reserialized model) matters, since it also
catches tampering in transit, not just an unknown caller. Tested by signing
one payload and sending a different one under that signature: rejected.

The frontend's Simulate button signs with the same secret via Web Crypto,
purely because it's standing in for the rail in this demo (see caveats).

**Rejections carry a `reason_code` enum alongside the free-text `reason`.**
The admin panel's filter chips key off `reason_code`, not the prose. I'd
originally pattern-matched the reason string and realized that'd silently
break the first time someone reworded a message.

**Replaced `assert loan is not None` with a real `raise`.** Already
unreachable given `_rejection_reason`'s contract, but `assert` disappears
under `-O`, and it's the only thing standing between a future refactor
breaking that contract and a bare `NoneType` crash.

**The overpayment/payoff decision compares via Decimal, not the raw float
columns.** `Loan.outstanding` (`models.py`) is `total_repayable - total_paid`
in plain float, and that subtraction can drift below the true remaining
balance before any rounding happens — e.g. `10000.0 - 1028.88` comes out to
`8971.119999999999`, not `8971.12`. A naive `amount > outstanding` check
would then reject a borrower's exact final installment as an overpayment,
even though it's the precisely correct payoff amount. `outstanding_decimal`
(`loans.py`) recomputes straight from the two raw columns via
`Decimal(str(x))` instead, and both the overpayment check and the
payoff/balance update in `payments.py` go through it. This is a mitigation,
not a fix: the columns are still `Float` (see "Money is Float" below), so
this only protects the comparisons/arithmetic that matter, not the storage
format itself. Regression test:
`test_accumulated_float_drift_does_not_falsely_reject_exact_payoff`.

**Non-positive/NaN `amount` is a 422, not a stored rejection.**
`PaymentIn.amount` requires `> 0`. Consistent with how every other malformed
field already behaves (bad `loan_id`, missing `external_ref`, etc.), shape
validation fails before it ever reaches `receive_payment`; only things that
are shape-valid but fail for a business reason (unknown loan, overpayment,
duplicate) get recorded.

## Edge cases covered (tests)

Unknown loan, inactive loan (cancelled/paid_off/written_off), duplicate
redelivery, overpayment, exact payoff, missing/invalid signature, tampered
body, accumulated float drift falsely blocking an exact payoff, and both
concurrency races above (same `external_ref` redelivered, and two different
payments overdrawing the same loan).

Beyond the automated suite, I also tested manually with Postman (signed
webhook calls against the real signature scheme, including deliberately
wrong/missing signatures) and in the browser (Simulate/Resend, switching
tabs, the admin panel's filters) against the running app, not just through
pytest.

## What I'd flag before this ships

- **Money is `Float`**, inherited from the existing schema. The Decimal fix
  above protects the comparisons/arithmetic that matter, not the storage
  format; real money still needs `Numeric`/integer minor units.
- **Overpayment rejects instead of crediting** (see above).
- **The webhook signature proves integrity, not freshness.** It's HMAC over
  the raw body, so a tampered body fails verification, but there's no bound
  timestamp or nonce, so a captured valid request/signature could in
  principle be replayed later and would still verify. In practice a
  byte-identical replay just gets caught by the `external_ref` duplicate
  check downstream, but that's a side effect of the idempotency check, not a
  dedicated replay defense at the auth layer. A production signature scheme
  should bind a timestamp (with a tolerance window) into what's signed, the
  way Paystack/Stripe do.
- **Signing secret is a hardcoded constant**, shared across every channel. In
  reality this needs a secret store, rotatable, per-provider.
- **The frontend holds the signing secret.** Only okay because Simulate is
  playing the rail's role in this demo. A real frontend should never see it.
- **No idempotency at the HTTP layer.** Serialization stops a double-apply,
  but a redelivery that loses the race gets `200 rejected`, not a `200` that
  looks like the original success. Fine for retry-on-5xx callers, not for
  ones expecting an `Idempotency-Key`-style contract.
- **Concurrency correctness relies on whole-transaction serialization**
  (`BEGIN IMMEDIATE`), coarser than it needs to be: every webhook call
  blocks every other one, not just same-loan ones. Fine at this scale; on
  Postgres the `SELECT ... FOR UPDATE` already in `_lock_loan` gives the same
  correctness with real per-loan concurrency, just untested here since this
  only runs on SQLite.
- **No pagination/filtering** on `GET /payment-events` or `GET /audit-log`.
  Fine for a demo feed, not production volume.
- **`GET /audit-log` has no auth**, unlike the webhook. Fine for a local
  demo, not for a real deployment.
- **No structured logging/metrics** on reconciliation outcomes.
- **The locking pattern (`with serialized_write(): ... db.commit()`) only
  lives in `receive_payment`**, not pulled into a shared function. There's
  only one write path, so an abstraction with one caller felt premature.
  Worth doing the moment there's a second write path.
- **Frontend signing needs `crypto.subtle`**, which requires a secure
  context (HTTPS or `localhost`). Demoing over a LAN IP would silently break
  Simulate/Resend.
- **README's auth section is stale.** Still describes the old
  `X-Webhook-Token` scheme. Left README.md untouched per instructions; the
  real scheme is documented here and in `auth.py`'s docstring.

## Extensions built

- **Provider signature verification (backend).** Swapped the shared
  `X-Webhook-Token` for a real HMAC-SHA512 check (see above).
- **Admin reconciliation & issues panel (frontend).** Second tab
  (`Admin.jsx`): health stats (applied/rejected/failure rate), a filterable
  table of rejected events by `reason_code`, and an activity trail backed by
  a new `GET /audit-log` endpoint. Drove the running app in a headless
  browser to check it, and caught a real bug this way: `/audit-log` wasn't in
  the Vite dev proxy allowlist, so it silently 404'd to `index.html` instead
  of hitting the API.

## How I used AI

The frontend (admin panel, Simulate/Resend signing) was built end-to-end
with Claude Code. On the backend, I wrote the `receive_payment`
reconciliation logic and wired up the auth switch myself; Claude's role
there was refactoring the logic into named helpers, fixing the concurrency
bug, and writing the test cases (edge cases above + the concurrency and
tampered-signature tests). Places I pushed back rather than took the first
answer:

- Asked it to walk through how real lenders handle overpayment before
  picking a policy, instead of letting it default to one.
- First concurrency pass was just `with_for_update()`, which is a no-op on
  SQLite: correctness theater, since that's the only DB this actually runs
  against. Next pass added a partial unique index as a backstop; I cut that
  too since it fights the "record every event" requirement. Landed on the
  `BEGIN IMMEDIATE` hook instead, with the multithreaded test as the check
  before and after.
- Had it pull `receive_payment` into named helpers once the logic settled,
  readability only, confirmed no behavior change via the full suite.
- Had it add the Decimal fix for the float-drift overpayment/payoff bug and
  the second concurrency test (different payments racing the same loan),
  with a hand-verified repro (`10000.0 - 1028.88` in plain float, checked in
  a one-off interpreter session) before trusting either the bug or the fix.
- For the admin panel, didn't stop at "it compiles." Had it drive both dev
  servers in a headless browser (simulate payments, switch tabs, click
  filters, Resend a duplicate) and check for console errors. That's what
  caught the audit-log proxy bug.
- Ran a multi-pass automated review (correctness, simplification, structural,
  a removed-behavior diff) before calling it done. Real issues it caught:
  unvalidated negative/NaN amounts, the `BEGIN IMMEDIATE` hook eagerly
  locking plain GETs, a `threading.local()` that only stayed request-scoped
  by accident, the admin panel pattern-matching rejection text instead of
  using a real code, a stripped `assert` as the only null-guard, the HTTP
  response being read after the lock released, a dead 501 branch left from
  the stub, and the missing SQLite dialect guard. It also flagged things I
  left as documented tradeoffs rather than fixing: `/audit-log` has no auth,
  the locking pattern isn't structurally enforced yet, and README is stale.
