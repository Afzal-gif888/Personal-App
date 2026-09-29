"""Append-only audit trail for security-relevant actions."""

import uuid

from sqlalchemy.orm import Session

from app.core.logging import redact, request_id_var
from app.models import AuditLog


def record(
    db: Session,
    action: str,
    *,
    user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id=None,
    ip_address: str | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            request_id=request_id_var.get(),
            ip_address=ip_address,
            details=redact(details or {}),
        )
    )
