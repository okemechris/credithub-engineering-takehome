"""Behaviour spec for the payment webhook you're building.

Contract (see README): POST /webhooks/payments with an X-Webhook-Token header
and a JSON body {external_ref, loan_id, amount, channel?}. A payment is
reconciled ON RECEIPT — recorded and immediately applied or rejected.

- 401 without a valid token.
- On success: the event is "applied", a repayment is recorded, the loan
  balance drops, and the loan closes when fully repaid. Return {event, loan}.
- Reject (status "rejected" + reason, still 200) when it can't be applied: the
  loan isn't active, the loan is unknown, a duplicate external_ref was already
  applied (rails redeliver), or the amount overpays.

These fail against the stub — make them pass, then add your own.
"""

TOK = {"X-Webhook-Token": "dev-webhook-secret"}


def _pay(ref, loan_id, amount, channel="paystack"):
    return {"external_ref": ref, "loan_id": loan_id, "amount": amount, "channel": channel}


def test_webhook_applies_payment_and_reduces_outstanding(client):
    r = client.post("/webhooks/payments", json=_pay("R-1", 1, 20000), headers=TOK)
    assert r.status_code == 200
    assert r.json()["event"]["status"] == "applied"
    assert client.get("/loans/1").json()["outstanding"] == 36000


def test_exact_payoff_closes_loan(client):
    client.post("/webhooks/payments", json=_pay("R-2", 1, 56000), headers=TOK)
    assert client.get("/loans/1").json()["status"] == "paid_off"


def test_duplicate_external_ref_is_rejected(client):
    client.post("/webhooks/payments", json=_pay("R-1", 1, 20000), headers=TOK)
    r = client.post("/webhooks/payments", json=_pay("R-1", 1, 20000), headers=TOK)  # redelivery
    assert r.json()["event"]["status"] == "rejected"
    assert client.get("/loans/1").json()["outstanding"] == 36000  # applied once only


def test_payment_for_cancelled_loan_is_rejected(client):
    r = client.post("/webhooks/payments", json=_pay("R-3", 2, 100), headers=TOK)  # loan 2 cancelled
    assert r.json()["event"]["status"] == "rejected"
    assert client.get("/loans/2").json()["outstanding"] == 11000  # untouched


def test_unknown_loan_is_rejected(client):
    r = client.post("/webhooks/payments", json=_pay("R-4", 999, 100), headers=TOK)
    assert r.json()["event"]["status"] == "rejected"


def test_overpayment_is_rejected(client):
    r = client.post("/webhooks/payments", json=_pay("R-5", 1, 999999), headers=TOK)
    assert r.json()["event"]["status"] == "rejected"
    assert client.get("/loans/1").json()["outstanding"] == 56000  # untouched


def test_webhook_requires_a_valid_token(client):
    r = client.post("/webhooks/payments", json=_pay("R-6", 1, 100))  # no token
    assert r.status_code == 401


# --- provided endpoint (this already passes) ---

def test_feed_endpoint_lists_events(client):
    assert client.get("/payment-events").status_code == 200
