from pathlib import Path

import polars as pl


def extract_csv(path: Path) -> pl.LazyFrame:
    return pl.scan_csv(
        path,
        infer_schema=False,
    ).rename(lambda name: name.strip())
