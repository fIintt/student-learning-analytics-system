import polars as pl


def transform_accounts(lf: pl.LazyFrame) -> pl.LazyFrame:
    return (
        lf.with_columns(
            pl.col("account_id").str.strip_chars(),
            pl.col("username").str.strip_chars().str.to_lowercase(),
            pl.col("password_hash").str.strip_chars(),
            pl.col("role").str.strip_chars().str.to_lowercase(),
            pl.col("student_id").str.strip_chars(),
            pl.col("staff_id").str.strip_chars().str.to_uppercase(),
        )
        .with_columns(pl.col(pl.String).replace("", None))
        .unique(maintain_order=True)
    )
