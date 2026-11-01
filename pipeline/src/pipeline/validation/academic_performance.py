import polars as pl

from pipeline.validation.validate import is_blank, validate_data

_REQUIRED_ACADEMIC_PERFORMANCE_COLUMNS = [
    "student_id",
    "academic_year",
    "semester",
    "registered_credits",
    "passed_credits",
    "failed_credits",
    "semester_gpa",
    "cumulative_gpa",
]


def _build_academic_performance_rules(
    valid_student_ids: list[str],
) -> dict[str, pl.Expr]:
    return {
        "missing_student_id": is_blank("student_id"),
        "unknown_student_id": (
            ~pl.col("student_id").is_in(valid_student_ids)
        ).fill_null(False),
        "missing_academic_year": is_blank("academic_year"),
        "invalid_academic_year": (
            ~pl.col("academic_year").str.contains(r"^[0-9]{4}-[0-9]{4}$")
        ).fill_null(False),
        "missing_semester": pl.col("semester").is_null(),
        "invalid_semester": (~pl.col("semester").is_in([1, 2])).fill_null(False),
        "duplicate_key": pl.struct(
            "student_id", "academic_year", "semester"
        ).is_duplicated(),
        "missing_registered_credits": pl.col("registered_credits").is_null(),
        "missing_passed_credits": pl.col("passed_credits").is_null(),
        "missing_failed_credits": pl.col("failed_credits").is_null(),
        "negative_credits": (
            (pl.col("registered_credits") < 0)
            | (pl.col("passed_credits") < 0)
            | (pl.col("failed_credits") < 0)
        ).fill_null(False),
        "credits_mismatch": (
            pl.col("passed_credits") + pl.col("failed_credits")
            > pl.col("registered_credits")
        ).fill_null(False),
        "missing_semester_gpa": pl.col("semester_gpa").is_null(),
        "missing_cumulative_gpa": pl.col("cumulative_gpa").is_null(),
        "semester_gpa_out_of_range": (
            ~pl.col("semester_gpa").is_between(0, 4)
        ).fill_null(False),
        "cumulative_gpa_out_of_range": (
            ~pl.col("cumulative_gpa").is_between(0, 4)
        ).fill_null(False),
    }


def validate_academic_performance(
    lf: pl.LazyFrame, valid_student_ids: list[str]
) -> tuple[pl.LazyFrame, pl.LazyFrame]:
    return validate_data(
        lf,
        _REQUIRED_ACADEMIC_PERFORMANCE_COLUMNS,
        _build_academic_performance_rules(valid_student_ids),
    )
