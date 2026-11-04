"""Copy pipeline accounts into BE users without updating pipeline tables or existing credentials."""
import re
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, inspect, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Role, Student, User


def sync_accounts(db: Session) -> dict:
    inspector = inspect(db.get_bind())
    if not inspector.has_table("accounts") or not inspector.has_table("staff"):
        raise HTTPException(503, detail="Chưa có bảng accounts/staff; hãy chạy pipeline trước")
    # Serialize sync runs. Per-row savepoints also handle concurrent account creation by API.
    db.execute(text("SELECT pg_advisory_xact_lock(110011005)"))
    rows = db.execute(text("""SELECT a.account_id, a.username, a.password_hash, a.role,
        a.student_id, a.staff_id, s.name AS staff_name, s.email AS staff_email
        FROM accounts a LEFT JOIN staff s ON s.staff_id=a.staff_id ORDER BY a.username""")).mappings().all()
    report = {"total": len(rows), "created": 0, "skipped": 0, "conflicts": 0, "items": []}
    for row in rows:
        username = (row["username"] or "").strip().lower()
        reason = None
        try:
            source_id = str(UUID(str(row["account_id"])))
            role = Role(row["role"])
        except (ValueError, TypeError):
            reason = "invalid_source_account"
        if not username or len(username) > 255 or any(c.isspace() for c in username):
            reason = "invalid_username"
        if reason:
            report["conflicts"] += 1
            report["items"].append(dict(username=username, status="conflict", reason=reason, user_id=None))
            continue
        existing = db.scalar(select(User).where(User.source_account_id == source_id))
        if existing:
            # Source changes never silently change access or reset a password already changed in BE.
            if (existing.username.lower(), existing.role, existing.student_id, existing.staff_id) != (
                    username, role, row["student_id"], row["staff_id"]):
                report["conflicts"] += 1
                status, reason = "conflict", "source_identity_changed"
            else:
                report["skipped"] += 1
                status, reason = "skipped", "already_linked_preserved"
            report["items"].append(dict(username=username, status=status, reason=reason, user_id=existing.id))
            continue
        student = db.get(Student, row["student_id"]) if row["student_id"] else None
        if role == Role.VIEWER:
            valid_owner = student is not None and row["staff_id"] is None
            full_name, email = (student.name if student else username), None
        else:
            valid_owner = bool(row["staff_id"] and row["staff_name"] and row["student_id"] is None)
            full_name, email = row["staff_name"], row["staff_email"]
            email = email.strip().lower() if email else None
        if not valid_owner:
            reason = "invalid_account_owner"
        elif not re.fullmatch(r"\$2[aby]\$(?:0[4-9]|[12][0-9]|3[01])\$[./A-Za-z0-9]{53}", row["password_hash"] or ""):
            reason = "unsupported_password_hash"
        if reason is None:
            conditions = [func.lower(User.username) == username]
            if row["student_id"]:
                conditions.append(User.student_id == row["student_id"])
            if email:
                conditions.append(func.lower(User.email) == email)
            if db.scalar(select(User.id).where(or_(*conditions)).limit(1)):
                reason = "existing_user_conflict"
        if reason:
            report["conflicts"] += 1
            report["items"].append(dict(username=username, status="conflict", reason=reason, user_id=None))
            continue
        try:
            with db.begin_nested():
                user = User(username=username, email=email, full_name=full_name, role=role,
                    student_id=row["student_id"], staff_id=row["staff_id"], source_account_id=source_id,
                    hashed_password=row["password_hash"], must_change_password=True, is_active=True)
                db.add(user)
                db.flush()
            report["created"] += 1
            report["items"].append(dict(username=username, status="created", reason=None, user_id=user.id))
        except IntegrityError:
            report["conflicts"] += 1
            report["items"].append(dict(username=username, status="conflict", reason="existing_user_conflict", user_id=None))
    db.commit()
    return report
