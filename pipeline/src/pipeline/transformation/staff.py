import polars as pl


def transform_staff(lf: pl.LazyFrame) -> pl.LazyFrame:
    return (
        lf.with_columns(
            pl.col("staff_id").str.strip_chars().str.to_uppercase(),
            pl.col("name").str.strip_chars().str.to_titlecase(),
            pl.col("email").str.strip_chars().str.to_lowercase(),
            pl.col("department").str.strip_chars(),
            pl.col("type").str.strip_chars().str.to_lowercase(),
        )
        .with_columns(pl.col(pl.String).replace("", None))
        .unique(maintain_order=True)
    )
