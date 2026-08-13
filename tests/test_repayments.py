"""Behaviour spec for the endpoint you're building.

These describe the REQUIRED behaviour and currently FAIL against the stub.
Make them pass, then add your own — they are a starting point, not exhaustive.
The request shape below ({"amount": ..., "idempotency_key": ...}) is a
suggestion; if you change it, update these tests to match.
"""


def test_partial_repayment_reduces_outstanding(client):
    r = client.post(
        "/loans/1/repayments", json={"amount": 20000}, headers={"X-Role": "system"}
    )
    assert r.status_code == 201
    assert client.get("/loans/1").json()["outstanding"] == 36000


def test_full_repayment_marks_loan_paid_off(client):
    client.post(
        "/loans/1/repayments", json={"amount": 56000}, headers={"X-Role": "system"}
    )
    loan = client.get("/loans/1").json()
    assert loan["status"] == "paid_off"
    assert loan["outstanding"] == 0


def test_cannot_repay_a_cancelled_loan(client):
    r = client.post(
        "/loans/2/repayments", json={"amount": 100}, headers={"X-Role": "system"}
    )
    assert r.status_code == 409


def test_unauthorised_role_is_rejected(client):
    r = client.post(
        "/loans/1/repayments", json={"amount": 100}, headers={"X-Role": "customer"}
    )
    assert r.status_code == 403


def test_idempotent_retry_does_not_double_apply(client):
    body = {"amount": 10000, "idempotency_key": "retry-abc"}
    client.post("/loans/1/repayments", json=body, headers={"X-Role": "system"})
    client.post("/loans/1/repayments", json=body, headers={"X-Role": "system"})  # retry
    # The retry must NOT be applied twice.
    assert client.get("/loans/1").json()["total_paid"] == 10000
