from datetime import datetime, UTC
from pathlib import Path

import polars as pl


def load_rejected_data(
    rows: pl.DataFrame,
    root: Path,
    source_file_hash: str,
) -> int:
    out_dir = root / source_file_hash[:12]
    out_path = out_dir / "rejected.parquet"

    if not rows.height:
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)

    rows.with_columns(pl.lit(datetime.now(UTC)).alias("rejected_at")).write_parquet(
        out_path
    )

    return rows.height


def load_processed_data(
    rows: pl.DataFrame,
    root: Path,
    source_file_hash: str,
) -> int:
    out_dir = root / source_file_hash[:12]
    out_path = out_dir / "processed.parquet"

    if not rows.height:
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)

    rows.write_parquet(out_path)

    return rows.height
