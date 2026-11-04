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


def fetch_program_ids(conn: psycopg.Connection) -> list[str]:
    return [
        row[0] for row in conn.execute("SELECT program_id FROM programs").fetchall()
    ]


def fetch_student_ids(conn: psycopg.Connection) -> list[str]:
    return [
        row[0] for row in conn.execute("SELECT student_id FROM students").fetchall()
    ]


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
                (program_id, 
                 program_name_vi, 
                 program_name_en, 
                 major_code,
                 program_type, 
                 first_cohort_year, 
                 last_cohort_year)
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT 
                (program_id)
            DO UPDATE
            SET program_name_vi   = EXCLUDED.program_name_vi,
                program_name_en   = EXCLUDED.program_name_en,
                major_code        = EXCLUDED.major_code,
                program_type      = EXCLUDED.program_type,
                first_cohort_year = EXCLUDED.first_cohort_year,
                last_cohort_year  = EXCLUDED.last_cohort_year
            WHERE
                (programs.program_name_vi, 
                 programs.program_name_en, 
                 programs.major_code,
                 programs.program_type, 
                 programs.first_cohort_year, 
                 programs.last_cohort_year)
            IS DISTINCT FROM
                (EXCLUDED.program_name_vi,
                 EXCLUDED.program_name_en,
                 EXCLUDED.major_code,
                 EXCLUDED.program_type,
                 EXCLUDED.first_cohort_year,
                 EXCLUDED.last_cohort_year)
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
                (student_id, 
                 name, 
                 program_id, 
                 cohort, 
                 academic_status)
            VALUES 
                (%s, %s, %s, %s, %s)
            ON CONFLICT 
                (student_id) 
            DO UPDATE 
            SET name            = EXCLUDED.name,
                program_id      = EXCLUDED.program_id,
                cohort          = EXCLUDED.cohort,
                academic_status = EXCLUDED.academic_status
            WHERE 
                (students.name, 
                 students.program_id, 
                 students.cohort, 
                 students.academic_status)
            IS DISTINCT FROM
                (EXCLUDED.name, 
                 EXCLUDED.program_id, 
                 EXCLUDED.cohort, 
                 EXCLUDED.academic_status)
            """,
            records,
        )

        return cursor.rowcount


def load_academic_performance(conn: psycopg.Connection, rows: pl.DataFrame) -> int:
    records = rows.select(
        [
            "student_id",
            "academic_year",
            "semester",
            "registered_credits",
            "passed_credits",
            "failed_credits",
            "semester_gpa",
            "cumulative_gpa",
        ]
    ).iter_rows()

    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO academic_performance 
                (student_id, academic_year, semester, registered_credits, 
                 passed_credits, failed_credits, semester_gpa, cumulative_gpa)
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT 
                (student_id, academic_year, semester) 
            DO UPDATE 
            SET registered_credits = EXCLUDED.registered_credits,
                passed_credits     = EXCLUDED.passed_credits,
                failed_credits     = EXCLUDED.failed_credits,
                semester_gpa       = EXCLUDED.semester_gpa,
                cumulative_gpa     = EXCLUDED.cumulative_gpa
            WHERE 
                (academic_performance.registered_credits,
                 academic_performance.passed_credits,
                 academic_performance.failed_credits,
                 academic_performance.semester_gpa,
                 academic_performance.cumulative_gpa)
            IS DISTINCT FROM
                (EXCLUDED.registered_credits,
                 EXCLUDED.passed_credits,
                 EXCLUDED.failed_credits,
                 EXCLUDED.semester_gpa,
                 EXCLUDED.cumulative_gpa)
            """,
            records,
        )

        return cursor.rowcount


def load_staff(conn: psycopg.Connection, rows: pl.DataFrame) -> int:
    records = rows.select(
        ["staff_id", "name", "email", "department", "type"]
    ).iter_rows()

    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO staff 
                (staff_id, name, email, department, type)
            VALUES 
                (%s, %s, %s, %s, %s)
            ON CONFLICT 
                (staff_id)
            DO UPDATE
            SET name = EXCLUDED.name,
                email = EXCLUDED.email,
                department = EXCLUDED.department,
                type = EXCLUDED.type
            WHERE 
                (staff.name, 
                 staff.email, 
                 staff.department, 
                 staff.type)
            IS DISTINCT FROM
                (EXCLUDED.name, 
                 EXCLUDED.email, 
                 EXCLUDED.department, 
                 EXCLUDED.type)
            """,
            records,
        )

        return cursor.rowcount


def load_accounts(conn: psycopg.Connection, rows: pl.DataFrame) -> int:
    student_rows, staff_rows = (
        rows.filter(pl.col("student_id").is_not_null()),
        rows.filter(pl.col("staff_id").is_not_null()),
    )

    student_records, staff_records = (
        student_rows.select(
            ["account_id", "username", "password_hash", "role", "student_id"]
        ).iter_rows(),
        staff_rows.select(
            ["account_id", "username", "password_hash", "role", "staff_id"]
        ).iter_rows(),
    )

    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO accounts
                (account_id, 
                 username, 
                 password_hash, 
                 role, 
                 student_id, 
                 staff_id)
            VALUES 
                (%s, %s, %s, %s, %s, NULL)
            ON CONFLICT 
                (student_id)
            DO UPDATE
            SET username = EXCLUDED.username,
                password_hash = EXCLUDED.password_hash
            WHERE
                (accounts.username, 
                 accounts.password_hash)
            IS DISTINCT FROM
                (EXCLUDED.username, 
                 EXCLUDED.password_hash)
            """,
            student_records,
        )

        student_inserted = cursor.rowcount

        cursor.executemany(
            """
            INSERT INTO accounts
                (account_id, 
                username, 
                password_hash, 
                role, 
                student_id,
                staff_id)
            VALUES 
                (%s, %s, %s, %s, NULL, %s)
            ON CONFLICT 
                (staff_id)
            DO UPDATE
            SET username = EXCLUDED.username,
                password_hash = EXCLUDED.password_hash,
                role = EXCLUDED.role
            WHERE
                (accounts.username, 
                 accounts.password_hash, 
                 accounts.role)
            IS DISTINCT FROM
                (EXCLUDED.username, 
                 EXCLUDED.password_hash, 
                 EXCLUDED.role)
            """,
            staff_records,
        )

        staff_inserted = cursor.rowcount

        return student_inserted + staff_inserted
