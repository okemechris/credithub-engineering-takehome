"""Repayment + early-settlement endpoints.

>>> THIS IS YOUR TASK. <<<

The endpoints below are stubs. Remove them and implement the real behaviour
described in README.md. You own the request/response schemas, the transaction
boundary, and the tests.
"""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/loans/{loan_id}/repayments", status_code=501)
def create_repayment(loan_id: int):
    """TODO(candidate): record a repayment against a loan. See README.md."""
    raise HTTPException(status_code=501, detail="not implemented — this is your task")


@router.get("/loans/{loan_id}/settlement-quote", status_code=501)
def settlement_quote(loan_id: int):
    """TODO(candidate): early full-settlement quote. See README.md (extension)."""
    raise HTTPException(status_code=501, detail="not implemented — this is your task")
