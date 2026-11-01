import polars as pl


def transform_programs(lf: pl.LazyFrame) -> pl.LazyFrame:
    return (
        lf.with_columns(pl.col(pl.String).str.strip_chars())
        .with_columns(pl.col("program_id").str.to_uppercase())
        .with_columns(pl.col(pl.String).replace("", None))
        .with_columns(pl.col("program_type").replace({"Advanced (EP)": "EP"}))
        .with_columns(
            pl.col("first_cohort_year").cast(pl.Int16, strict=False),
            pl.col("last_cohort_year").cast(pl.Int16, strict=False),
        )
        .unique(maintain_order=True)
    )
