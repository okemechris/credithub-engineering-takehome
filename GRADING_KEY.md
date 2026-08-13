# GRADING KEY — INTERNAL ONLY

**Do NOT include this file when you send the package to candidates.**
(Delete `GRADING_KEY.md` before zipping / sharing the repo.)

The task is engineered so the naïve AI-generated answer is *subtly wrong*. A
candidate can make the provided spec pass and still miss the things that matter
in a lender. Score the dimensions below; the two "top signals" are the ones
that separate a hire-worthy senior from paste-and-pray.

## Planted traps (did they catch these unprompted?)

| Trap | Where it bites | Green flag | Red flag |
|---|---|---|---|
| **★ Float money** | `Loan.principal/total_repayable/total_paid` are `Float`. Accumulating repayments drifts; an "exact" payoff (see the `Ngozi Eze` seed, 37333.33) won't hit 0 with `==`. | Uses `Decimal`, or compares with a tolerance / rounds at the right boundary; calls the `Float` schema out in `NOTES.md`. | Compares money with `==`; leaves a loan "not quite" paid off; off-by-cents. |
| **★ Idempotency / double-apply** | A retried POST applies the payment twice. | Dedups on an idempotency key (or equivalent) so a retry is a no-op; returns the original result. | No dedup — retry doubles `total_paid`. |
| **Audit atomicity** | Audit must commit with the payment. | Audit row added to the same session/transaction; rolls back on failure. | Commits payment then writes audit separately (orphan/none on failure). |
| **Overpayment** | Paying more than outstanding. | Explicit, defensible choice (reject / cap at outstanding / record credit) and it's tested. | Silent negative outstanding. |
| **State machine** | Repaying a cancelled/written-off/paid-off loan. | Rejected with a clear 4xx (409). | Allowed. |
| **AuthZ** | Wrong role can post. | Correct role(s) enforced; others 403. | Endpoint open or wrong roles. |
| **Concurrency** *(stretch)* | Two simultaneous repayments race. | Row lock / serialisation; no lost update. | Read-modify-write race that overpays. |

★ = top signal.

## Scoring the AI-first dimension (this is the whole point)

From `NOTES.md` **and** the 30-min walkthrough:
- **Green:** can explain every line; can point to where AI got it wrong and how
  they caught it; flags real production risks (the `Float` schema, missing
  bureau of edge cases, migration concerns) unprompted.
- **Red:** can't explain parts of their own diff; no risks flagged;
  "the tests pass, so it's done."

## Quick verdict
- **Strong hire:** catches **Float** + **double-apply**, clean audit atomicity,
  tests that would catch a regression, and can defend it all live.
- **Maybe:** happy path solid, catches one of the two top traps, honest
  `NOTES.md`.
- **Pass:** provided spec passes but both top traps missed, `==` on money, and
  can't explain the diff.

## How to run their submission
```bash
pip install -r requirements.txt
pytest -q            # their tests + the provided spec should be green
# then read NOTES.md and do the walkthrough call
```
