from typing import LiteralString, cast

import psycopg
import polars as pl

from pipeline.config import (
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
    SCHEMA_DIR,
)


def connect_postgres() -> psycopg.Connection:
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=10,
        options="-c lock_timeout=10000",  # millisecond
    )


def create_schemas(conn: psycopg.Connection) -> None:
    for file in sorted(SCHEMA_DIR.glob("*.sql")):
        conn.execute(cast(LiteralString, file.read_text(encoding="utf-8")))


def load_programs(conn: psycopg.Connection, rows: pl.DataFrame) -> int:
    records = rows.select(
        [
            "program_id",
            "program_name_vi",
            "program_name_en",
            "major_code",
            "program_type",
            "first_cohort_year",
            "last_cohort_year",
        ]
    ).iter_rows()

    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO programs
                (program_id, program_name_vi, program_name_en, major_code,
                 program_type, first_cohort_year, last_cohort_year)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (program_id) DO NOTHING
            """,
            records,
        )
        return cursor.rowcount


def load_students(conn: psycopg.Connection, rows: pl.DataFrame) -> int:
    records = rows.select(
        ["student_id", "name", "program_id", "cohort", "academic_status"]
    ).iter_rows()

    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO students 
                (student_id, name, program_id, cohort, academic_status)
            VALUES 
                (%s, %s, %s, %s, %s)
            ON CONFLICT (student_id) DO NOTHING
            """,
            records,
        )

        return cursor.rowcount
