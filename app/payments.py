"""Payment ingestion + reconciliation.

Provided (working): list the payment feed, and *simulate* an incoming payment
(a fake gateway callback that drops a new ``pending`` event).

>>> YOUR TASK is the reconciliation endpoint — see the stub at the bottom. <<<
"""

import random
import uuid

from fastapi import APIRouter, Depends, HTTPException

from .db import get_db
from .models import Loan, LoanStatus, PaymentEvent, PaymentStatus

router = APIRouter()


def _event_out(e: PaymentEvent) -> dict:
    return {
        "id": e.id,
        "external_ref": e.external_ref,
        "loan_id": e.loan_id,
        "amount": e.amount,
        "channel": e.channel,
        "status": e.status.value,
        "reason": e.reason,
        "received_at": e.received_at.isoformat() if e.received_at else None,
        "processed_at": e.processed_at.isoformat() if e.processed_at else None,
    }


@router.get("/payment-events")
def list_payment_events(db=Depends(get_db)):
    """The payments feed (newest first) — provided."""
    events = db.query(PaymentEvent).order_by(PaymentEvent.id.desc()).all()
    return [_event_out(e) for e in events]


@router.post("/simulate/payment", status_code=201)
def simulate_payment(db=Depends(get_db)):
    """Simulate an incoming payment from a rail — provided.

    Drops a new ``pending`` PaymentEvent against a random active loan. Sometimes
    the amount is the exact outstanding (an early settlement), so you'll see
    payoffs too. This is the 'a payment just landed' half of the loop; applying
    it is your job.
    """
    actives = db.query(Loan).filter(Loan.status == LoanStatus.active).all()
    if not actives:
        raise HTTPException(status_code=400, detail="no active loans to simulate against")
    loan = random.choice(actives)
    amount = round(random.choice([5000.0, 10000.0, 20000.0, loan.outstanding]), 2)
    event = PaymentEvent(
        external_ref=f"SIM-{uuid.uuid4().hex[:10].upper()}",
        loan_id=loan.id,
        amount=amount,
        channel=random.choice(["paystack", "gsi", "cbs"]),
        status=PaymentStatus.pending,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _event_out(event)


@router.post("/payment-events/{event_id}/apply", status_code=501)
def apply_payment_event(event_id: int):
    """TODO(candidate): reconcile ('tick off') a pending payment against its loan.

    Remove this stub and implement it. See README.md for the full contract.
    """
    raise HTTPException(status_code=501, detail="not implemented — this is your task")
