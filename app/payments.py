"""Payment ingestion + reconciliation.

Provided (working): the payments feed (``GET /payment-events``).

>>> YOUR TASK is the webhook that reconciles an incoming payment ON RECEIPT —
    ``POST /webhooks/payments``. See the stub at the bottom and README.md. <<<

The frontend's "Simulate incoming payment" button POSTs a synthetic payment to
this webhook — exactly as a real gateway/rail would. There is no separate
"apply" step: a payment arrives and is reconciled in the same call.
"""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.auth import require_webhook_signature

from .db import get_db, serialized_write
from .loans import loan_out, outstanding_decimal
from .models import Loan, LoanStatus, PaymentEvent, PaymentStatus, Repayment, RejectionReason

router = APIRouter()


class PaymentIn(BaseModel):
    external_ref: str
    loan_id: int
    amount: float = Field(gt=0)  # a rail never reports a zero/negative/NaN payment
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
        "reason_code": e.reason_code.value if e.reason_code else None,
        "received_at": e.received_at.isoformat() if e.received_at else None,
        "processed_at": e.processed_at.isoformat() if e.processed_at else None,
    }


@router.get("/payment-events")
def list_payment_events(db=Depends(get_db)):
    """The payments feed (newest first) — provided."""
    events = db.query(PaymentEvent).order_by(PaymentEvent.id.desc()).all()
    return [_event_out(e) for e in events]


def _new_event(body: PaymentIn) -> PaymentEvent:
    return PaymentEvent(
        external_ref=body.external_ref,
        loan_id=body.loan_id,
        amount=body.amount,
        channel=body.channel,
        status=PaymentStatus.pending,
        processed_at=datetime.now(timezone.utc),
    )


def _lock_loan(db: Session, loan_id: int) -> Loan | None:
    """Fetch the loan and hold its row lock for the rest of the transaction.

    ``with_for_update()`` is what a row-locking DB would use to serialize two
    webhooks racing on the same loan; the actual serialization on this app's
    SQLite backend comes from the eager ``BEGIN IMMEDIATE`` in ``db.py``,
    which forces the whole transaction to wait for the write lock up front.
    Either way, a second concurrent request only proceeds once the first has
    committed, so its checks below run against fresh, already-committed state.
    """
    return db.query(Loan).filter(Loan.id == loan_id).with_for_update().one_or_none()


def _rejection_reason(
    db: Session, loan: Loan | None, external_ref: str, amount: float
) -> tuple[RejectionReason, str] | None:
    """Why this payment can't be applied (a machine code + human message), or
    None if it can. Callers that need to classify a rejection (e.g. the admin
    panel's issue filter) should switch on the code, not pattern-match the
    message — the message is free text for a human, not a stable contract.
    """
    if loan is None:
        return RejectionReason.unknown_loan, "unknown loan"
    if loan.status != LoanStatus.active:
        return RejectionReason.closed_loan, f"loan is {loan.status.value}, not active"

    already_applied = (
        db.query(PaymentEvent)
        .filter(
            PaymentEvent.external_ref == external_ref,
            PaymentEvent.status == PaymentStatus.applied,
        )
        .first()
    )
    if already_applied is not None:
        return RejectionReason.duplicate, "duplicate external_ref already applied"
    if Decimal(str(amount)) > outstanding_decimal(loan):
        return RejectionReason.overpayment, "payment amount exceeds outstanding balance"
    return None


def _apply(db: Session, event: PaymentEvent, loan: Loan, amount: float) -> None:
    """Tick the payment off against the loan: repayment, balance, payoff, audit."""
    db.flush()  # assign event.id for the repayment FK
    loan.total_paid = float(Decimal(str(loan.total_paid)) + Decimal(str(amount)))
    if outstanding_decimal(loan) <= 0:
        loan.status = LoanStatus.paid_off
    event.status = PaymentStatus.applied
    db.add(Repayment(loan_id=loan.id, payment_event_id=event.id, amount=amount))
    record_audit(
        db,
        action="payment.applied",
        entity="loan",
        entity_id=loan.id,
        actor="webhook",
        detail=f"applied {amount} via external_ref={event.external_ref}",
    )


@router.post("/webhooks/payments")
def receive_payment(
    body: PaymentIn, db=Depends(get_db), _raw_body: bytes = Depends(require_webhook_signature)
):
    """A payment just arrived from a rail — reconcile it on receipt: record it,
    then apply it to the loan or reject it, all in one transaction.

    Wrapped in ``serialized_write()`` so this transaction (and only this one -
    plain GETs stay on SQLite's normal deferred ``BEGIN``) takes SQLite's write
    lock up front. See ``db.py`` for why.
    """
    with serialized_write():
        event = _new_event(body)
        db.add(event)

        loan = _lock_loan(db, body.loan_id)
        rejection = _rejection_reason(db, loan, body.external_ref, body.amount)

        if rejection is not None:
            event.status = PaymentStatus.rejected
            event.reason_code, event.reason = rejection
        elif loan is not None:
            _apply(db, event, loan, body.amount)
        else:
            # _rejection_reason only returns None (i.e. "applicable") once it
            # has found a loan, so this is unreachable — but a KeyError deep
            # in _apply on a future logic change would be a worse failure
            # mode than a clear error here.
            raise RuntimeError("no rejection reason but no loan to apply to")

        # Serialize the response from the in-memory objects *before* commit
        # releases the write lock, not after: `expire_on_commit` (the
        # sessionmaker default) would otherwise make the next attribute
        # access after commit issue a fresh SELECT, which could pick up a
        # different request's commit that lands in the gap between our
        # commit and that read — this loan's fields in the response might
        # then reflect a payment this request never decided on. Capturing
        # the response here means it always reflects exactly this request's
        # own transaction.
        db.flush()  # assign event.id (autoincrement PK) before serializing
        response = {"event": _event_out(event), "loan": loan_out(loan) if loan is not None else None}

        db.commit()

    return response
