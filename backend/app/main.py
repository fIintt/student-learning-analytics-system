import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.errors import register_exception_handlers
from app.db.session import SessionLocal, init_db
from app.services import group_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        init_db()
        with SessionLocal() as db:
            group_service.sync_groups(db)  # nhóm mới cho chương trình × khoá mà pipeline vừa nạp
    except RuntimeError as exc:
        logger.warning(
            "Khởi động không đầy đủ: %s — Các API cần dữ liệu pipeline sẽ trả lỗi.", exc
        )
    yield


def create_app(*, create_tables: bool = True) -> FastAPI:
    app = FastAPI(title="M11. Phân tích học tập", version="1.0.0",
                  lifespan=lifespan if create_tables else None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
