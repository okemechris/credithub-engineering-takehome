"""Audit helper.

Every mutation on the platform must leave an audit record. This helper adds
the row to the CURRENT session so it commits in the SAME transaction as the
business change — a rollback discards both, a success persists both. Do not
commit here; the caller owns the transaction boundary.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .db import get_db
from .models import AuditLog

router = APIRouter()


def record_audit(
    db: Session,
    *,
    action: str,
    entity: str,
    entity_id,
    actor: str,
    detail: str | None = None,
) -> None:
    db.add(
        AuditLog(
            action=action,
            entity=entity,
            entity_id=str(entity_id),
            actor=actor,
            detail=detail,
        )
    )


def _log_out(a: AuditLog) -> dict:
    return {
        "id": a.id,
        "action": a.action,
        "entity": a.entity,
        "entity_id": a.entity_id,
        "actor": a.actor,
        "detail": a.detail,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/audit-log")
def list_audit_log(db=Depends(get_db)):
    """Activity trail for the admin panel (newest first)."""
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).all()
    return [_log_out(a) for a in logs]
