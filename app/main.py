"""FastAPI app entry point."""

from fastapi import FastAPI

from . import models  # noqa: F401 — register models on Base
from .db import Base, engine
from .loans import router as loans_router
from .repayments import router as repayments_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CreditHub take-home — loan servicing slice")
app.include_router(loans_router)
app.include_router(repayments_router)


@app.get("/health")
def health():
    return {"status": "ok"}
