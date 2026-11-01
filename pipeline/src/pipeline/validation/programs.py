from pipeline.config import RAW_PROGRAMS_PATH
from pipeline.utils import is_blank
import polars as pl

from pipeline.utils import validate_data

_REQUIRED_PROGRAMS_COLUMNS = [
    "program_id",
    "program_name_vi",
    "program_name_en",
    "major_code",
    "program_type",
    "first_cohort_year",
    "last_cohort_year",
]
_VALID_PROGRAM_TYPES = ["Standard", "Advanced (EP)", "POHE", "CLC", "TT"]


_PROGRAMS_RULES: dict[str, pl.Expr] = {
    "missing_program_id": is_blank("program_id"),
    "duplicate_program_id": pl.col("program_id").is_duplicated(),
    "missing_program_name_vi": is_blank("program_name_vi"),
    "missing_program_name_en": is_blank("program_name_en"),
    "missing_major_code": is_blank("major_code"),
    "invalid_major_code": (~pl.col("major_code").str.contains(r"^[0-9]{7}$")).fill_null(
        False
    ),
    "missing_program_type": is_blank("program_type"),
    "invalid_program_type": (
        ~pl.col("program_type").is_in(_VALID_PROGRAM_TYPES)
    ).fill_null(False),
    "missing_first_cohort_year": pl.col("first_cohort_year").is_null(),
    "missing_last_cohort_year": pl.col("last_cohort_year").is_null(),
    "invalid_cohort_year_range": (
        pl.col("last_cohort_year") < pl.col("first_cohort_year")
    ).fill_null(False),
}


def validate_programs(
    lf: pl.LazyFrame,
) -> tuple[pl.LazyFrame, pl.LazyFrame]:
    return validate_data(
        lf,
        _REQUIRED_PROGRAMS_COLUMNS,
        _PROGRAMS_RULES,
    )
