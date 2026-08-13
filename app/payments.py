"""Payment ingestion + reconciliation.

Provided (working): the payments feed (``GET /payment-events``).

>>> YOUR TASK is the webhook that reconciles an incoming payment ON RECEIPT —
    ``POST /webhooks/payments``. See the stub at the bottom and README.md. <<<

The frontend's "Simulate incoming payment" button POSTs a synthetic payment to
this webhook — exactly as a real gateway/rail would. There is no separate
"apply" step: a payment arrives and is reconciled in the same call.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .db import get_db
from .models import PaymentEvent

router = APIRouter()


class PaymentIn(BaseModel):
    external_ref: str
    loan_id: int
    amount: float
    channel: str = "paystack"


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


@router.post("/webhooks/payments", status_code=501)
def receive_payment(body: PaymentIn):
    """TODO(candidate): a payment just arrived from a rail — reconcile it on
    receipt. Remove this stub and implement it. See README.md for the contract.
    """
    raise HTTPException(status_code=501, detail="not implemented — this is your task")
