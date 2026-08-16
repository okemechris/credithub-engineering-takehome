"""Read endpoints for loans (provided — working)."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from .db import get_db
from .models import Loan

router = APIRouter()


def outstanding_decimal(loan: Loan) -> Decimal:
    """``Loan.outstanding`` recomputed in Decimal, not the model's float
    property. The property subtracts in plain float, so drift from earlier
    payments can already be baked into the result before any Decimal
    conversion happens (e.g. ``10000.0 - 1028.88`` comes out to
    ``8971.119999999999``, not ``8971.12``) — recomputing straight from the
    two raw columns instead avoids that.
    """
    return Decimal(str(loan.total_repayable)) - Decimal(str(loan.total_paid))


def loan_out(loan: Loan) -> dict:
    return {
        "id": loan.id,
        "borrower_name": loan.borrower_name,
        "principal": loan.principal,
        "total_repayable": loan.total_repayable,
        "total_paid": loan.total_paid,
        "outstanding": float(outstanding_decimal(loan)),
        "status": loan.status.value,
    }


@router.get("/loans")
def list_loans(db=Depends(get_db)):
    return [loan_out(loan) for loan in db.query(Loan).all()]


@router.get("/loans/{loan_id}")
def get_loan(loan_id: int, db=Depends(get_db)):
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="loan not found")
    return loan_out(loan)
