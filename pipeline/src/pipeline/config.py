import os
from pathlib import Path

from dotenv import load_dotenv

# Roots
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent

load_dotenv(REPO_ROOT / ".env")


def require_env(name: str) -> str:
    value = os.environ.get(name)

    if not value or not value.strip():
        raise ValueError(f"Required environment variable {name!r} is missing or empty")

    return value


# Database
DB_USER = require_env("DB_USER")
DB_PASSWORD = require_env("DB_PASSWORD")
DB_HOST = require_env("DB_HOST")
DB_PORT = int(require_env("DB_PORT"))
DB_NAME = require_env("DB_NAME")

# Paths
RAW_DIR = PROJECT_ROOT / "data" / "raw"
REJECTED_DIR = PROJECT_ROOT / "data" / "rejected"
SCHEMA_DIR = PROJECT_ROOT / "sql" / "schemas"

RAW_STUDENTS_PATH = RAW_DIR / "students.csv"
RAW_PROGRAMS_PATH = RAW_DIR / "programs.csv"
RAW_ACADEMIC_PERFORMANCE_PATH = RAW_DIR / "academic_performance.csv"

REJECTED_STUDENTS_PATH = REJECTED_DIR / "students"
REJECTED_PROGRAMS_PATH = REJECTED_DIR / "programs"
REJECTED_ACADEMIC_PERFORMANCE_PATH = REJECTED_DIR / "academic_performance"
