from pipeline.validation.validate import is_blank
import polars as pl

from pipeline.validation.validate import validate_data

_REQUIRED_ACCOUNT_COLUMNS = [
    "account_id",
    "username",
    "password_hash",
    "role",
    "student_id",
    "staff_id",
]

_VALID_ACCOUNT_ROLES = ["viewer", "reviewer", "admin"]

_ACCOUNT_RULES: dict[str, pl.Expr] = {
    "missing_account_id": pl.col("account_id").is_null(),
    "missing_username": is_blank("username"),
    "missing_password_hash": is_blank("password_hash"),
    "missing_role": is_blank("role"),
    "invalid_role": (~pl.col("role").is_in(_VALID_ACCOUNT_ROLES)).fill_null(False),
    "missing_student_id": (
        (pl.col("role") == "viewer") & pl.col("student_id").is_null()
    ).fill_null(False),
    "missing_staff_id": (
        (pl.col("role").is_in(["reviewer", "admin"])) & pl.col("staff_id").is_null()
    ).fill_null(False),
    "invalid_account_owner": (
        ((pl.col("role") == "viewer") & pl.col("staff_id").is_not_null())
        | (
            (pl.col("role").is_in(["reviewer", "admin"]))
            & pl.col("student_id").is_not_null()
        )
    ).fill_null(False),
}


def validate_accounts(
    lf: pl.LazyFrame,
) -> tuple[pl.LazyFrame, pl.LazyFrame]:
    return validate_data(
        lf,
        _REQUIRED_ACCOUNT_COLUMNS,
        _ACCOUNT_RULES,
    )
