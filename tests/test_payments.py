"""Behaviour spec for the reconciliation endpoint you're building.

Contract (see README): POST /payment-events/{id}/apply with an X-Role header.
- 403 if the role may not reconcile; 404 if the event doesn't exist.
- On success the event becomes "applied", a repayment is recorded, the loan
  balance drops, and the loan closes when fully repaid.
- Applying an already-applied event is a no-op (idempotent).
- A payment whose external_ref was already applied is a duplicate → "rejected".
- A payment for a non-active loan → "rejected".

These fail against the stub — make them pass, then add your own.
"""

H = {"X-Role": "system"}


def test_apply_reduces_outstanding_and_ticks_off(client):
    r = client.post("/payment-events/1/apply", headers=H)
    assert r.status_code == 200
    assert r.json()["event"]["status"] == "applied"
    assert client.get("/loans/1").json()["outstanding"] == 36000


def test_apply_is_idempotent(client):
    client.post("/payment-events/1/apply", headers=H)
    client.post("/payment-events/1/apply", headers=H)  # retry / double-click
    assert client.get("/loans/1").json()["outstanding"] == 36000  # not 16000


def test_duplicate_external_ref_is_rejected(client):
    client.post("/payment-events/1/apply", headers=H)       # ref R-1 applied
    r = client.post("/payment-events/3/apply", headers=H)   # ref R-1 again (redelivery)
    assert r.json()["event"]["status"] == "rejected"
    assert client.get("/loans/1").json()["outstanding"] == 36000  # applied once only


def test_payment_for_cancelled_loan_is_rejected(client):
    r = client.post("/payment-events/2/apply", headers=H)   # loan 2 is cancelled
    assert r.json()["event"]["status"] == "rejected"
    assert client.get("/loans/2").json()["outstanding"] == 11000  # untouched


def test_apply_requires_an_authorised_role(client):
    r = client.post("/payment-events/1/apply", headers={"X-Role": "customer"})
    assert r.status_code == 403


def test_apply_unknown_event_returns_404(client):
    assert client.post("/payment-events/999/apply", headers=H).status_code == 404


# --- provided endpoints (these already pass) ---

def test_feed_lists_pending_events(client):
    events = client.get("/payment-events").json()
    assert len(events) == 3
    assert all(e["status"] == "pending" for e in events)


def test_simulate_creates_a_pending_event(client):
    before = len(client.get("/payment-events").json())
    r = client.post("/simulate/payment")
    assert r.status_code == 201
    assert r.json()["status"] == "pending"
    assert len(client.get("/payment-events").json()) == before + 1
