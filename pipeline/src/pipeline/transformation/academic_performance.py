import polars as pl


def transform_academic_performance(lf: pl.LazyFrame) -> pl.LazyFrame:
    return (
        lf.with_columns(pl.col(pl.String).str.strip_chars())
        .with_columns(
            pl.col("student_id"),
            pl.col("academic_year").str.replace_all("/", "-"),
        )
        .with_columns(pl.col(pl.String).replace("", None))
        .with_columns(
            pl.col("semester").cast(pl.Int16, strict=False),
            pl.col("registered_credits").cast(pl.Int16, strict=False),
            pl.col("passed_credits").cast(pl.Int16, strict=False),
            pl.col("failed_credits").cast(pl.Int16, strict=False),
            pl.col("semester_gpa").cast(pl.Float64, strict=False),
            pl.col("cumulative_gpa").cast(pl.Float64, strict=False),
        )
        .unique(maintain_order=True)
    )
