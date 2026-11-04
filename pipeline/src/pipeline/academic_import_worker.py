"""Worker used by the backend's preview/confirm academic import flow."""

import json
import sys
from pathlib import Path

import polars as pl
import psycopg

from pipeline.ingestion.extract import extract_csv
from pipeline.transformation.academic_performance import transform_academic_performance
from pipeline.validation.academic_performance import validate_academic_performance

REQUIRED_COLUMNS = {
    "student_id",
    "academic_year",
    "semester",
    "registered_credits",
    "passed_credits",
    "failed_credits",
    "semester_gpa",
    "cumulative_gpa",
}
VALUE_COLUMNS = (
    "registered_credits",
    "passed_credits",
    "failed_credits",
    "semester_gpa",
    "cumulative_gpa",
)


def _json_value(value):
    if hasattr(value, "item"):
        value = value.item()
    return value


def _row_values(row: dict) -> dict:
    return {key: _json_value(row.get(key)) for key in (
        "student_id", "academic_year", "semester", *VALUE_COLUMNS,
    )}


def _set_search_path(conn: psycopg.Connection, schema: str) -> None:
    conn.execute("SELECT set_config('search_path', %s, false)", (schema,))


def _scope(conn: psycopg.Connection, uploaded_by: int) -> set[str] | None:
    user_row = conn.execute("SELECT role FROM users WHERE id = %s", (uploaded_by,)).fetchone()
    if user_row is None:
        raise ValueError("Không tìm thấy người tải dữ liệu")
    role = user_row[0]
    if role == "admin":
        return None
    rows = conn.execute(
        """
        SELECT s.student_id
        FROM students s
        JOIN learner_groups g ON g.program_id = s.program_id AND g.cohort = s.cohort
        JOIN user_group_access uga ON uga.group_id = g.id
        WHERE uga.user_id = %s
        """,
        (uploaded_by,),
    ).fetchall()
    return {row[0] for row in rows}


def _existing(conn: psycopg.Connection) -> dict[tuple, tuple]:
    rows = conn.execute(
        """
        SELECT student_id, academic_year, semester, registered_credits,
               passed_credits, failed_credits, semester_gpa, cumulative_gpa
        FROM academic_performance
        """
    ).fetchall()
    return {
        (row[0], row[1], row[2]): (
            row[3], row[4], row[5], float(row[6]), float(row[7])
        )
        for row in rows
    }


def _same_values(row: dict, existing: tuple) -> bool:
    return tuple(row[column] for column in VALUE_COLUMNS) == existing


def _prepare(conn: psycopg.Connection, context: dict) -> tuple[dict, list[dict], list[dict]]:
    path = Path(context["file_path"])
    if path.stat().st_size > context["max_bytes"]:
        raise ValueError("File CSV vượt quá giới hạn dung lượng cho phép")

    raw = extract_csv(path)
    columns = set(raw.collect_schema().names())
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError(f"Thiếu cột CSV: {', '.join(sorted(missing))}")

    transformed = transform_academic_performance(raw).with_row_index("__row_number", offset=2)
    student_ids = [row[0] for row in conn.execute("SELECT student_id FROM students").fetchall()]
    validated, rejected = validate_academic_performance(transformed, student_ids)
    raw_count = raw.select(pl.len()).collect().item()
    transformed_df, valid_df, rejected_df = pl.collect_all([transformed, validated, rejected])
    if raw_count > context["max_rows"]:
        raise ValueError("File CSV vượt quá giới hạn số dòng cho phép")

    scope = _scope(conn, context["uploaded_by"])
    existing = _existing(conn)
    errors = []
    prepared = []
    new_rows = []

    for row in rejected_df.iter_rows(named=True):
        errors.append({
            "row_number": int(row["__row_number"]),
            "reason": row["reject_reason"],
            "values": _row_values(row),
        })

    for row in valid_df.iter_rows(named=True):
        values = _row_values(row)
        key = (values["student_id"], values["academic_year"], values["semester"])
        if scope is not None and values["student_id"] not in scope:
            errors.append({"row_number": int(row["__row_number"]), "reason": "learner_outside_scope", "values": values})
        elif key in existing and _same_values(values, existing[key]):
            prepared.append({**values, "disposition": "unchanged"})
        elif key in existing:
            errors.append({"row_number": int(row["__row_number"]), "reason": "existing_record_conflict", "values": values})
        else:
            prepared.append({**values, "row_number": int(row["__row_number"]), "disposition": "new"})
            new_rows.append(values)

    summary = {
        "total_rows": raw_count,
        "duplicated_rows": raw_count - transformed_df.height,
        "new_rows": len(new_rows),
        "unchanged_rows": sum(row["disposition"] == "unchanged" for row in prepared),
        "rejected_rows": len(errors),
    }
    return summary, prepared, errors


def _update_job(conn: psycopg.Connection, import_id: int, summary: dict, prepared: list[dict], errors: list[dict], status: str, error_message=None) -> None:
    conn.execute("DELETE FROM academic_import_errors WHERE import_id = %s", (import_id,))
    if errors:
        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO academic_import_errors (import_id, row_number, reason, \"values\") VALUES (%s, %s, %s, %s)",
                [(import_id, item["row_number"], item["reason"], json.dumps(item["values"], ensure_ascii=False)) for item in errors],
            )
    conn.execute(
        """
        UPDATE academic_imports
        SET status = %s, total_rows = %s, duplicated_rows = %s, new_rows = %s,
            unchanged_rows = %s, rejected_rows = %s, inserted_rows = %s,
            prepared_rows = %s, error_message = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (status, summary["total_rows"], summary["duplicated_rows"], summary["new_rows"],
         summary["unchanged_rows"], summary["rejected_rows"], summary.get("inserted_rows", 0),
         json.dumps(prepared, ensure_ascii=False), error_message, import_id),
    )


def _insert_new(conn: psycopg.Connection, rows: list[dict]) -> tuple[int, list[dict]]:
    inserted = 0
    conflicts = []
    for row in rows:
        result = conn.execute(
            """
            INSERT INTO academic_performance
                (student_id, academic_year, semester, registered_credits, passed_credits,
                 failed_credits, semester_gpa, cumulative_gpa)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (student_id, academic_year, semester) DO NOTHING
            """,
            tuple(row[column] for column in ("student_id", "academic_year", "semester", *VALUE_COLUMNS)),
        )
        if result.rowcount:
            inserted += result.rowcount
        else:
            conflicts.append({
                "row_number": row["row_number"],
                "reason": "existing_record_conflict",
                "values": _row_values(row),
            })
    return inserted, conflicts


def run(context: dict) -> None:
    with psycopg.connect(context["dsn"]) as conn:
        _set_search_path(conn, context["schema"])
        try:
            summary, prepared, errors = _prepare(conn, context)
            if context["mode"] == "confirm":
                inserted, conflicts = _insert_new(conn, [row for row in prepared if row["disposition"] == "new"])
                errors.extend(conflicts)
                summary["rejected_rows"] += len(conflicts)
                summary["inserted_rows"] = inserted
                status = "completed"
            else:
                summary["inserted_rows"] = 0
                status = "ready"
            _update_job(conn, context["import_id"], summary, prepared, errors, status)
            conn.commit()
        except Exception as exc:
            conn.rollback()
            conn.execute(
                "UPDATE academic_imports SET status = 'failed', error_message = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (str(exc)[:2000], context["import_id"]),
            )
            conn.commit()
            raise


if __name__ == "__main__":
    run(json.load(sys.stdin))