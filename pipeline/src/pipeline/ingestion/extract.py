import hashlib
from pathlib import Path

import polars as pl


def hash_file(path: Path, chunk_size: int = 1 << 20) -> str:
    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def extract_csv(path: Path) -> pl.LazyFrame:
    return pl.scan_csv(
        path,
        infer_schema=False,
    ).rename(lambda name: name.strip())
