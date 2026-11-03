from pipeline.validation.validate import is_blank
import polars as pl

from pipeline.validation.validate import validate_data

_REQUIRED_STUDENT_COLUMNS = [
    "student_id",
    "name",
    "program_id",
    "cohort",
    "academic_status",
]

_VALID_STUDENT_STATUSES = ["studying", "graduated", "suspended"]


def _create_student_rules(valid_program_ids: list[str]) -> dict[str, pl.Expr]:
    return {
        "missing_student_id": is_blank("student_id"),
        "invalid_student_id": (
            ~pl.col("student_id").str.contains(r"^11[0-9]{6}$")
        ).fill_null(False),
        "duplicate_student_id": pl.col("student_id").is_duplicated(),
        "missing_name": is_blank("name"),
        "missing_program_id": is_blank("program_id"),
        "unknown_program_id": (
            ~pl.col("program_id").is_in(valid_program_ids)
        ).fill_null(False),
        "missing_cohort": pl.col("cohort").is_null(),
        "missing_academic_status": is_blank("academic_status"),
        "invalid_academic_status": (
            ~pl.col("academic_status").is_in(_VALID_STUDENT_STATUSES)
        ).fill_null(False),
    }


def validate_students(
    lf: pl.LazyFrame, valid_program_ids: list[str]
) -> tuple[pl.LazyFrame, pl.LazyFrame]:
    return validate_data(
        lf,
        _REQUIRED_STUDENT_COLUMNS,
        _create_student_rules(valid_program_ids),
    )
