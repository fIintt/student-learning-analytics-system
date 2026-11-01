import polars as pl

def transform_students(lf: pl.LazyFrame) -> pl.LazyFrame:
    cohort = pl.col("cohort").str.strip_chars()
    
    return (
        lf.with_columns(
            pl.col("student_id").str.strip_chars(),
            pl.col("name").str.strip_chars().str.to_titlecase(),
            pl.col("program_id").str.strip_chars().str.to_uppercase(),
            pl.col("academic_status").str.strip_chars().str.to_lowercase(),
            pl.when(cohort.str.starts_with("K"))
              .then(cohort.str.slice(1).cast(pl.Int16, strict=False) + 1958)
              .otherwise(cohort.cast(pl.Int16, strict=False))
              .alias("cohort"),
        )
        .with_columns(pl.col(pl.String).replace("", None))
        .unique(maintain_order=True)
    )