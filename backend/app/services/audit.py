from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.models import AuditLog, User


def log_action(
    db: Session,
    *,
    user: Optional[User],
    action: str,
    module: str,
    target_type: str,
    target_id: Optional[str],
    message: str,
    detail_json: Optional[Dict[str, Any]] = None,
) -> None:
    entry = AuditLog(
        user_id=user.id if user else None,
        action=action,
        module=module,
        target_type=target_type,
        target_id=target_id,
        message=message,
        detail_json=detail_json or {},
    )
    db.add(entry)
