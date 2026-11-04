from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[3] / ".env", env_file_encoding="utf-8", extra="ignore")

    # Biến dùng chung với Pipeline — luôn đồng bộ khi chỉ sửa một chỗ trong .env
    db_user: str = "postgres"
    db_password: str = "change-me"
    db_host: str = "localhost"
    db_port: int = 5433
    db_name: str = "student_learning"

    # Nếu đặt DATABASE_URL thủ công trong .env thì ưu tiên dùng nó
    database_url: str | None = None
    test_database_url: str | None = None
    pipeline_dir: Path = Path(__file__).resolve().parents[3] / "pipeline"
    pipeline_python: str | None = None
    academic_import_dir: Path = Path(__file__).resolve().parents[2] / "data" / "academic_imports"
    academic_import_max_bytes: int = 10 * 1024 * 1024
    academic_import_max_rows: int = 50000
    academic_import_timeout_seconds: int = 300

    secret_key: str = "dev-secret-chi-dung-khi-thieu-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    @property
    def effective_database_url(self) -> str:
        """Ưu tiên DATABASE_URL nếu có, ngược lại tự ghép từ các biến DB_*."""
        if self.database_url:
            return self.database_url
        return URL.create(
            "postgresql+psycopg", username=self.db_user, password=self.db_password,
            host=self.db_host, port=self.db_port, database=self.db_name,
        ).render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
