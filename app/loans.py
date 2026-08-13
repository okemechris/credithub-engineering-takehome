"""Read endpoints for loans (provided — working)."""

from fastapi import APIRouter, Depends, HTTPException

from .db import get_db
from .models import Loan

router = APIRouter()


def _loan_out(loan: Loan) -> dict:
    return {
        "id": loan.id,
        "borrower_name": loan.borrower_name,
        "principal": loan.principal,
        "total_repayable": loan.total_repayable,
        "total_paid": loan.total_paid,
        "outstanding": loan.outstanding,
        "status": loan.status.value,
    }


@router.get("/loans")
def list_loans(db=Depends(get_db)):
    return [_loan_out(loan) for loan in db.query(Loan).all()]


@router.get("/loans/{loan_id}")
def get_loan(loan_id: int, db=Depends(get_db)):
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="loan not found")
    return _loan_out(loan)
