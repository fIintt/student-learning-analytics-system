from datetime import datetime, UTC
from pathlib import Path

import polars as pl


def load_rejected_data(
    rows: pl.DataFrame, root: Path, source_file_hash: str
) -> int:
    out_dir = root / source_file_hash[:12]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "rejected.parquet"

    rows.with_columns(pl.lit(datetime.now(UTC)).alias("rejected_at")).write_parquet(
        out_path
    )

    return pl.scan_parquet(out_path).select(pl.len()).collect().item()
