"""ORM models for the loan-servicing slice.

Kept intentionally close to the real platform's shape — including the fact
that money is stored as ``Float``. Treat this as the production schema you've
inherited.
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

    repayments = relationship("Repayment", back_populates="loan")

    @property
    def outstanding(self) -> float:
        return self.total_repayable - self.total_paid


class Repayment(Base):
    __tablename__ = "repayments"

    id = Column(Integer, primary_key=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    loan = relationship("Loan", back_populates="repayments")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    action = Column(String, nullable=False)
    entity = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    detail = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
