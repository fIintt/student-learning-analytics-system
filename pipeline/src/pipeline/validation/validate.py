import polars as pl


def is_blank(col: str) -> pl.Expr:
    return pl.col(col).is_null() | (pl.col(col).str.strip_chars() == "")


def validate_data(
    lf: pl.LazyFrame, required_columns: list[str], rules: dict[str, pl.Expr]
) -> tuple[pl.LazyFrame, pl.LazyFrame]:
    missing = [
        col for col in required_columns if col not in lf.collect_schema().names()
    ]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    flagged = lf.with_columns(
        pl.concat_str(
            [
                pl.when(expr.fill_null(False)).then(pl.lit(name))
                for name, expr in rules.items()
            ],
            separator=";",
            ignore_nulls=True,
        ).alias("reject_reason")
    )

    validated = flagged.filter(pl.col("reject_reason") == "").drop("reject_reason")
    rejected = flagged.filter(pl.col("reject_reason") != "")

    return validated, rejected
