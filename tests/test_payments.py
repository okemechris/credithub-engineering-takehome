"""Behaviour spec for the payment webhook you're building.

Contract (see README): POST /webhooks/payments with an X-Webhook-Signature
header (HMAC-SHA512 over the raw body, see app/auth.py) and a JSON body
{external_ref, loan_id, amount, channel?}. A payment is reconciled ON
RECEIPT — recorded and immediately applied or rejected.

- 401 without a valid signature.
- On success: the event is "applied", a repayment is recorded, the loan
  balance drops, and the loan closes when fully repaid. Return {event, loan}.
- Reject (status "rejected" + reason, still 200) when it can't be applied: the
  loan isn't active, the loan is unknown, a duplicate external_ref was already
  applied (rails redeliver), or the amount overpays.

These fail against the stub — make them pass, then add your own.
"""

import hashlib
import hmac
import json

from app.auth import WEBHOOK_SIGNING_SECRET


def _pay(ref, loan_id, amount, channel="paystack"):
    return {"external_ref": ref, "loan_id": loan_id, "amount": amount, "channel": channel}


def _post(client, payload, *, signed=True):
    """POST a payment the way a real rail would: sign the exact raw bytes sent."""
    raw = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if signed:
        headers["X-Webhook-Signature"] = hmac.new(
            WEBHOOK_SIGNING_SECRET.encode(), raw, hashlib.sha512
        ).hexdigest()
    return client.post("/webhooks/payments", content=raw, headers=headers)


def test_webhook_applies_payment_and_reduces_outstanding(client):
    r = _post(client, _pay("R-1", 1, 20000))
    assert r.status_code == 200
    assert r.json()["event"]["status"] == "applied"
    assert r.json()["event"]["reason_code"] is None
    assert client.get("/loans/1").json()["outstanding"] == 36000


def test_exact_payoff_closes_loan(client):
    _post(client, _pay("R-2", 1, 56000))
    assert client.get("/loans/1").json()["status"] == "paid_off"


def test_duplicate_external_ref_is_rejected(client):
    _post(client, _pay("R-1", 1, 20000))
    r = _post(client, _pay("R-1", 1, 20000))  # redelivery
    assert r.json()["event"]["status"] == "rejected"
    assert r.json()["event"]["reason_code"] == "duplicate"
    assert client.get("/loans/1").json()["outstanding"] == 36000  # applied once only


def test_payment_for_cancelled_loan_is_rejected(client):
    r = _post(client, _pay("R-3", 2, 100))  # loan 2 cancelled
    assert r.json()["event"]["status"] == "rejected"
    assert r.json()["event"]["reason_code"] == "closed_loan"
    assert client.get("/loans/2").json()["outstanding"] == 11000  # untouched


def test_unknown_loan_is_rejected(client):
    r = _post(client, _pay("R-4", 999, 100))
    assert r.json()["event"]["status"] == "rejected"
    assert r.json()["event"]["reason_code"] == "unknown_loan"


def test_overpayment_is_rejected(client):
    r = _post(client, _pay("R-5", 1, 999999))
    assert r.json()["event"]["status"] == "rejected"
    assert r.json()["event"]["reason_code"] == "overpayment"
    assert client.get("/loans/1").json()["outstanding"] == 56000  # untouched


def test_webhook_requires_a_valid_signature(client):
    r = _post(client, _pay("R-6", 1, 100), signed=False)  # no signature header
    assert r.status_code == 401


def test_non_positive_amount_is_a_bad_request(client):
    """A rail never reports a zero/negative payment — that's a malformed
    request, not a business-level rejection, so it's a 422 and never becomes
    a stored PaymentEvent (unlike overpayment/duplicate/unknown-loan, which
    are all valid requests that fail reconciliation)."""
    r = _post(client, _pay("R-8", 1, -5000))
    assert r.status_code == 422
    assert client.get("/loans/1").json()["outstanding"] == 56000  # untouched
    assert not any(e["external_ref"] == "R-8" for e in client.get("/payment-events").json())


def test_webhook_rejects_a_tampered_body(client):
    """The signature covers the exact bytes sent — a body altered in transit
    (or forged without the secret) must not verify, even if it's well-formed
    JSON with a valid shape."""
    raw = json.dumps(_pay("R-7", 1, 100)).encode()
    sig = hmac.new(WEBHOOK_SIGNING_SECRET.encode(), raw, hashlib.sha512).hexdigest()
    tampered = json.dumps(_pay("R-7", 1, 999999)).encode()  # amount changed post-signing
    r = client.post(
        "/webhooks/payments",
        content=tampered,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": sig},
    )
    assert r.status_code == 401


def test_concurrent_redeliveries_apply_exactly_once(client):
    import threading

    results = []

    def fire():
        r = _post(client, _pay("RACE-1", 1, 20000))
        results.append(r.json()["event"]["status"])

    threads = [threading.Thread(target=fire) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count("applied") == 1
    assert results.count("rejected") == 9
    assert client.get("/loans/1").json()["outstanding"] == 36000


def test_concurrent_different_payments_never_overdraw_the_loan(client):
    """The redelivery race above only covers one `external_ref` racing itself
    - the duplicate check can't help here, since each of these is a distinct,
    legitimate payment. Ten threads each pay 20000 against loan #1's 56000
    outstanding: only two can ever fit (40000) before the third would overpay
    the remaining 16000. Serialization must make every thread see the
    balance as of its own turn, not a stale pre-race snapshot, or more than
    two would apply and the loan would go negative."""
    import threading

    results = []

    def fire(i):
        r = _post(client, _pay(f"RACE-DIFF-{i}", 1, 20000))
        results.append(r.json()["event"]["status"])

    threads = [threading.Thread(target=fire, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count("applied") == 2
    assert results.count("rejected") == 8
    assert client.get("/loans/1").json()["outstanding"] == 16000


def test_accumulated_float_drift_does_not_falsely_reject_exact_payoff(client):
    """`Loan.outstanding` subtracts in plain float
    (`total_repayable - total_paid`); after enough payments that subtraction
    can drift below the true remaining balance before any rounding happens
    (e.g. `10000.0 - 1028.88 == 8971.119999999999`, not `8971.12`). A naive
    `amount > outstanding` check would then reject a borrower's exact final
    installment as an overpayment. The reconciliation decision must compare
    via Decimal on the raw columns, not the float property, to avoid that."""
    from app.db import SessionLocal
    from app.models import Loan, LoanStatus

    db = SessionLocal()
    db.add(Loan(id=3, borrower_name="Drift Test", principal=9000,
                total_repayable=10000.0, total_paid=1028.88, status=LoanStatus.active))
    db.commit()
    db.close()

    r = _post(client, _pay("R-DRIFT", 3, 8971.12))
    assert r.json()["event"]["status"] == "applied"
    assert client.get("/loans/3").json()["status"] == "paid_off"


# --- provided endpoint (this already passes) ---

def test_feed_endpoint_lists_events(client):
    assert client.get("/payment-events").status_code == 200
