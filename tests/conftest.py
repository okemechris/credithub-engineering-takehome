import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Loan, LoanStatus, PaymentEvent


@pytest.fixture()
def client():
    """Fresh DB per test.

    Loans: #1 active (outstanding 56000), #2 cancelled.
    Payment events (all pending):
      #1 → loan 1, 20000, ref "R-1"
      #2 → loan 2, 100,   ref "R-2"   (loan is cancelled)
      #3 → loan 1, 20000, ref "R-1"   (DUPLICATE of #1 — a redelivery)
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add_all([
        Loan(id=1, borrower_name="Test One", principal=50000, total_repayable=56000, total_paid=0, status=LoanStatus.active),
        Loan(id=2, borrower_name="Closed", principal=10000, total_repayable=11000, total_paid=0, status=LoanStatus.cancelled),
        PaymentEvent(id=1, external_ref="R-1", loan_id=1, amount=20000, channel="paystack"),
        PaymentEvent(id=2, external_ref="R-2", loan_id=2, amount=100, channel="paystack"),
        PaymentEvent(id=3, external_ref="R-1", loan_id=1, amount=20000, channel="paystack"),
    ])
    db.commit()
    db.close()
    return TestClient(app)
