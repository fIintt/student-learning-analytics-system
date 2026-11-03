from pipeline.validation.validate import is_blank, validate_data
import polars as pl

_REQUIRED_STAFF_COLUMNS = [
    "staff_id",
    "name",
    "email",
    "department",
    "type",
]

_VALID_STAFF_TYPES = ["lecturer", "administrator"]

_STAFF_RULES: dict[str, pl.Expr] = {
    "missing_staff_id": is_blank("staff_id"),
    "duplicate_staff_id": pl.col("staff_id").is_duplicated(),
    "missing_name": is_blank("name"),
    "missing_email": is_blank("email"),
    "invalid_email": (
        ~pl.col("email").str.contains(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    ).fill_null(False),
    "missing_department": is_blank("department"),
    "missing_type": is_blank("type"),
    "invalid_type": (~pl.col("type").is_in(_VALID_STAFF_TYPES)).fill_null(False),
}


def validate_staff(
    lf: pl.LazyFrame,
) -> tuple[pl.LazyFrame, pl.LazyFrame]:
    return validate_data(
        lf,
        _REQUIRED_STAFF_COLUMNS,
        _STAFF_RULES,
    )
