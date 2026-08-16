"""ORM models for the loan-servicing slice.

Kept intentionally close to the real platform's shape — including the fact
that money is stored as ``Float``. Treat this as the production schema you've
inherited.

Flow: payments arrive as ``PaymentEvent`` rows (simulated gateway callbacks) in
``pending`` status. Reconciling them — matching to a loan, applying the money,
and ticking the event off — is the candidate's task.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LoanStatus(str, enum.Enum):
    active = "active"
    paid_off = "paid_off"
    cancelled = "cancelled"
    written_off = "written_off"


class PaymentStatus(str, enum.Enum):
    pending = "pending"    # landed, not yet reconciled
    applied = "applied"    # ticked off against a loan
    rejected = "rejected"  # could not be applied (bad loan state, duplicate, …)


class RejectionReason(str, enum.Enum):
    """Machine-stable classification of why a payment was rejected.

    ``PaymentEvent.reason`` is the human-readable message (for the feed/audit
    trail); this is what callers — e.g. the admin panel's issue filter chips
    — should actually switch on, instead of pattern-matching the prose in
    ``reason``, which can be reworded without warning.
    """

    unknown_loan = "unknown_loan"
    closed_loan = "closed_loan"
    duplicate = "duplicate"
    overpayment = "overpayment"


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True)
    borrower_name = Column(String, nullable=False)
    # NOTE: NGN amounts are stored as Float here, mirroring the platform's
    # current models. This is deliberate — do not assume it's correct.
    principal = Column(Float, nullable=False)
    total_repayable = Column(Float, nullable=False)  # principal + interest
    total_paid = Column(Float, nullable=False, default=0.0)
    status = Column(Enum(LoanStatus), nullable=False, default=LoanStatus.active)
    disbursed_at = Column(DateTime, default=_utcnow)

    @property
    def outstanding(self) -> float:
        return self.total_repayable - self.total_paid


class PaymentEvent(Base):
    """An incoming payment from a rail (gateway/GSI/CBS). Starts ``pending``.

    ``external_ref`` is the rail's own id for the payment — the idempotency key.
    It is NOT unique at the DB level, on purpose: real rails redeliver, so the
    same ``external_ref`` can arrive more than once, and every delivery that
    matches the webhook's expected shape is recorded as its own
    ``PaymentEvent`` row — including ones that go on to be rejected. (A
    request that *doesn't* match the shape at all — wrong types, missing
    fields, a non-positive amount — fails request validation before it's ever
    a candidate `PaymentIn`, the same as any REST endpoint; that's a 422, not
    a recorded-and-rejected event, since it was never a valid payment
    delivery to begin with.) Only one delivery may ever end up ``applied``
    for a given ``external_ref`` — that's enforced in application code (see
    ``payments._rejection_reason`` and the transaction-serialization note in
    ``db.py``), not by a DB constraint, so a redelivery that arrives after
    the original was applied is stored (for the audit trail) and rejected as
    a duplicate, but never touches the loan.
    """

    __tablename__ = "payment_events"

    id = Column(Integer, primary_key=True)
    external_ref = Column(String, nullable=False)  # rail's payment id (idempotency key)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False)
    amount = Column(Float, nullable=False)
    channel = Column(String, nullable=False, default="paystack")
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.pending)
    reason = Column(String, nullable=True)  # human-readable, why it was rejected
    reason_code = Column(Enum(RejectionReason), nullable=True)  # machine-stable, same
    received_at = Column(DateTime, default=_utcnow)
    processed_at = Column(DateTime, nullable=True)


class Repayment(Base):
    """Ledger row created when a payment event is applied to a loan."""

    __tablename__ = "repayments"

    id = Column(Integer, primary_key=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False)
    payment_event_id = Column(Integer, ForeignKey("payment_events.id"), nullable=True)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=_utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    action = Column(String, nullable=False)
    entity = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    detail = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
