"""Ghi nhật ký thao tác quan trọng.

record() chỉ thêm AuditLog vào session hiện tại, KHÔNG commit: nhật ký được lưu cùng transaction
với thao tác nghiệp vụ, nên thao tác thất bại thì nhật ký cũng không được ghi (và ngược lại).
"""

from sqlalchemy.orm import Session

from app.models import AuditLog, User

# action
METRIC_APPROVE = "metric.approve"
METRIC_REJECT = "metric.reject"
ALERT_CONFIRM = "alert.confirm"
ALERT_DISMISS = "alert.dismiss"
ALERT_SUPERSEDE = "alert.supersede"
ALERT_CARRY_FORWARD = "alert.carry_forward"
CASE_CREATE = "case.create"

# entity_type
METRIC_DEFINITION = "metric_definition"
ALERT = "alert"
SUPPORT_CASE = "support_case"


def record(db: Session, user: User | None, action: str, entity_type: str, entity_id: int | None,
           detail: dict | None = None) -> AuditLog:
    log = AuditLog(user_id=user.id if user else None, action=action, entity_type=entity_type,
                   entity_id=entity_id, detail=detail)
    db.add(log)
    return log
