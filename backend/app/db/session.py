from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str, **kwargs) -> Engine:
    """Chỉ dùng PostgreSQL, cho cả ứng dụng và bộ test."""
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql":
        raise ValueError("Backend chỉ hỗ trợ PostgreSQL.")
    if parsed.drivername == "postgresql":
        parsed = parsed.set(drivername="postgresql+psycopg")
    kwargs.setdefault("pool_pre_ping", True)
    return create_engine(parsed, **kwargs)


engine = make_engine(settings.effective_database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Ba bảng do pipeline tạo và nạp. Backend chỉ đọc, KHÔNG tạo (tránh mất ràng buộc CHECK của pipeline).
PIPELINE_TABLES = ("programs", "students", "academic_performance")


def init_db(bind: Engine = engine) -> None:
    """Tạo các bảng của backend. Yêu cầu pipeline đã chạy trước."""
    import app.models  # noqa: F401  (đăng ký toàn bộ bảng vào metadata)

    inspector = inspect(bind)
    missing = [t for t in PIPELINE_TABLES if not inspector.has_table(t)]
    if missing:
        raise RuntimeError(
            f"Chưa có bảng của pipeline trong CSDL: {', '.join(missing)}. "
            "Hãy bật PostgreSQL và chạy pipeline trước khi bật backend."
        )
    own_tables = [t for t in Base.metadata.sorted_tables if not t.info.get("pipeline")]
    Base.metadata.create_all(bind=bind, tables=own_tables)
    # Nâng cấp database cũ tại chỗ, không seed lại hoặc xoá lịch sử.
    with bind.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(110011002)"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(255)"))
        conn.execute(text("UPDATE users SET username=lower(trim(email)) WHERE username IS NULL"))
        conn.execute(text("ALTER TABLE users ALTER COLUMN username SET NOT NULL"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_username_ci ON users (lower(username))"))
        conn.execute(text("ALTER TABLE users ALTER COLUMN email DROP NOT NULL"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS source_account_id VARCHAR(36)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_source_account_id ON users (source_account_id)"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS staff_id VARCHAR(255)"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT false"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS student_id VARCHAR REFERENCES students(student_id)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_student_id ON users (student_id)"))
        conn.execute(text("ALTER TABLE metric_results ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1"))
        conn.execute(text("ALTER TABLE metric_results ADD COLUMN IF NOT EXISTS source_hash VARCHAR(64)"))
        conn.execute(text("ALTER TABLE academic_imports ADD COLUMN IF NOT EXISTS updated_rows INTEGER NOT NULL DEFAULT 0"))
        conn.execute(text("ALTER TABLE metric_results DROP CONSTRAINT IF EXISTS uq_metric_result_term"))
        conn.execute(text("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conrelid = 'metric_results'::regclass
                      AND conname = 'uq_metric_result_term_revision'
                ) THEN
                    ALTER TABLE metric_results ADD CONSTRAINT uq_metric_result_term_revision
                    UNIQUE (metric_definition_id, learner_id, academic_year, semester, revision);
                END IF;
            END; $$
        """))
