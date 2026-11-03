from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import Base, PIPELINE_TABLES, get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def readiness(db: Session = Depends(get_db)) -> JSONResponse | dict[str, str]:
    try:
        import app.models  # noqa: F401

        db.execute(text("SELECT 1"))
        required_tables = PIPELINE_TABLES + tuple(
            table.name for table in Base.metadata.sorted_tables if not table.info.get("pipeline")
        )
        missing = [table for table in required_tables if not inspect(db.bind).has_table(table)]
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "not_ready"})

    if missing:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "missing_tables": missing},
        )
    return {"status": "ready"}
