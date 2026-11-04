import hashlib
import json
import logging
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AcademicImport, AcademicImportError, Role, User
from app.schemas.academic_import import AcademicImportOut
from app.services.pagination import PageParams, paginate

logger = logging.getLogger(__name__)


def _command():
    root = settings.pipeline_dir.resolve()
    python = Path(settings.pipeline_python) if settings.pipeline_python else root / ".venv" / (
        "Scripts/python.exe" if os.name == "nt" else "bin/python")
    worker = root / "src/pipeline/academic_import_worker.py"
    if not python.is_file() or not worker.is_file():
        raise HTTPException(503, "Chưa chuẩn bị môi trường pipeline; hãy chạy uv sync trong thư mục pipeline")
    return [str(python.resolve()), str(worker)], root


def _file_path(storage_key: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", storage_key):
        raise ValueError("Invalid internal storage key")
    return settings.academic_import_dir.resolve() / storage_key / "source.csv"


def _expire_stale(db: Session, user: User):
    # shortcut: in-process background jobs; stale jobs fail safely and can be uploaded again after a crash.
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        seconds=2 * settings.academic_import_timeout_seconds + 60)
    stmt = update(AcademicImport).where(AcademicImport.status.in_(["processing", "importing"]),
                                       AcademicImport.updated_at < cutoff)
    if user.role != Role.ADMIN:
        stmt = stmt.where(AcademicImport.uploaded_by == user.id)
    result = db.execute(stmt.values(status="failed", error_message="Tác vụ bị gián đoạn; hãy upload lại file",
                                   updated_at=datetime.now(timezone.utc).replace(tzinfo=None)))
    db.commit()
    if result.rowcount:
        db.expire_all()


def get_import(db: Session, user: User, import_id: int, *, lock=False):
    stmt = select(AcademicImport).where(AcademicImport.id == import_id)
    if lock:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    job = db.scalar(stmt)
    if job is None:
        raise HTTPException(404, "Không tìm thấy lần nhập")
    if user.role != Role.ADMIN and job.uploaded_by != user.id:
        raise HTTPException(403, "Bạn không có quyền xem lần nhập này")
    return job


def detail(job: AcademicImport):
    return {**AcademicImportOut.model_validate(job).model_dump(),
            "preview_rows": [row for row in job.prepared_rows if row["disposition"] in ("new", "update", "inserted")][:20]}


def create(db: Session, user: User, file: UploadFile):
    _command()
    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    if not filename.lower().endswith(".csv") or len(filename) > 255:
        raise HTTPException(400, "Chỉ nhận file .csv có tên tối đa 255 ký tự")
    storage_key = uuid4().hex
    path = _file_path(storage_key)
    path.parent.mkdir(parents=True)
    sha, size = hashlib.sha256(), 0
    try:
        with path.open("xb") as target:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.academic_import_max_bytes:
                    raise HTTPException(413, "File CSV vượt quá giới hạn dung lượng cho phép")
                sha.update(chunk)
                target.write(chunk)
        if not size:
            raise HTTPException(400, "File CSV rỗng")
        job = AcademicImport(uploaded_by=user.id, filename=filename, storage_key=storage_key,
                             source_hash=sha.hexdigest(), status="processing")
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        path.parent.rmdir()
        raise
    finally:
        file.file.close()


def list_imports(db: Session, user: User, params: PageParams, status: str | None):
    _expire_stale(db, user)
    stmt = select(AcademicImport).order_by(AcademicImport.id.desc())
    if user.role != Role.ADMIN:
        stmt = stmt.where(AcademicImport.uploaded_by == user.id)
    if status is not None:
        stmt = stmt.where(AcademicImport.status == status)
    return paginate(db, stmt, params)


def get_detail(db: Session, user: User, import_id: int):
    _expire_stale(db, user)
    return detail(get_import(db, user, import_id))


def errors(db: Session, user: User, import_id: int, params: PageParams):
    get_import(db, user, import_id)
    return paginate(db, select(AcademicImportError).where(AcademicImportError.import_id == import_id)
                    .order_by(AcademicImportError.row_number, AcademicImportError.id), params)


def confirm(db: Session, user: User, import_id: int):
    _expire_stale(db, user)
    job = get_import(db, user, import_id, lock=True)
    if job.status in ("importing", "completed"):
        db.commit()
        return job, False
    if job.status != "ready":
        raise HTTPException(409, "Chỉ xác nhận được file đã kiểm tra xong ở trạng thái ready")
    _command()
    job.status = "importing"
    job.confirmed_by = user.id
    job.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return job, True


def run_job(bind, import_id: int, mode: str):
    try:
        command, root = _command()
        with Session(bind) as db:
            job = db.get(AcademicImport, import_id)
            if job is None:
                return
            context = {"import_id": job.id, "mode": mode, "uploaded_by": job.uploaded_by,
                       "file_path": str(_file_path(job.storage_key)),
                       "source_hash": job.source_hash, "max_rows": settings.academic_import_max_rows,
                       "max_bytes": settings.academic_import_max_bytes,
                       "schema": db.scalar(text("SELECT current_schema()")),
                       "dsn": bind.url.set(drivername="postgresql").render_as_string(hide_password=False)}
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(root / "src") + os.pathsep + environment.get("PYTHONPATH", "")
        environment["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(command, input=json.dumps(context), text=True, encoding="utf-8", errors="replace", capture_output=True,
                                cwd=root, env=environment, timeout=settings.academic_import_timeout_seconds)
        if result.returncode:
            detail = (result.stderr or result.stdout or "Worker không trả về thông tin lỗi").strip()
            raise RuntimeError(detail[-2000:])
    except Exception as exc:
        logger.warning("Academic import %s (%s) failed; no existing grades are overwritten", import_id, mode)
        error_message = next((line.strip() for line in reversed(str(exc).splitlines()) if line.strip()),
                             "Không chạy được pipeline hoặc tác vụ quá thời gian")
        with Session(bind) as db:
            db.execute(update(AcademicImport).where(AcademicImport.id == import_id,
                       AcademicImport.status.in_(["processing", "importing"]))
                       .values(status="failed", error_message=error_message[:2000],
                               updated_at=datetime.now(timezone.utc).replace(tzinfo=None)))
            db.commit()
