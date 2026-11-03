import logging
import time
from collections.abc import Callable
from pathlib import Path

from pipeline.logging_config import PipelineLogs
import polars as pl
import psycopg

from pipeline.ingestion.extract import extract_csv, hash_file
from pipeline.loading.parquet import load_processed_data, load_rejected_data


def run_pipeline(
    *,
    name: str,
    conn: psycopg.Connection,
    path: Path,
    rejected_path: Path,
    processed_path: Path,
    transform: Callable[[pl.LazyFrame], pl.LazyFrame],
    validate: Callable[[pl.LazyFrame], tuple[pl.LazyFrame, pl.LazyFrame]],
    load: Callable[[psycopg.Connection, pl.DataFrame], int],
) -> PipelineLogs:
    logger = logging.getLogger(f"pipeline.{name}")

    started_at = time.perf_counter()

    try:
        source_file_hash = hash_file(path)

        raw = extract_csv(path)
        transformed = transform(raw)
        validated, rejected = validate(transformed)

        read_df, deduped_df, valid_df, rejected_df = pl.collect_all(
            [raw.select(pl.len()), transformed.select(pl.len()), validated, rejected]
        )

        read = read_df.item()
        duplicates_dropped = read - deduped_df.item()
        validated_count = valid_df.height
        rejected_count = rejected_df.height

        if read != duplicates_dropped + rejected_count + validated_count:
            raise ValueError(
                f"Counts do not add up: read={read} duplicates={duplicates_dropped} "
                f"rejected={rejected_count} valid={validated_count}"
            )

        loaded = load(conn, valid_df)

        skipped = validated_count - loaded
        elapsed = time.perf_counter() - started_at

        loaded_rejected_count = load_rejected_data(
            rejected_df, rejected_path, source_file_hash
        )

        if loaded_rejected_count != rejected_count:
            raise ValueError(
                f"Rejected row persistence mismatch: "
                f"expected={rejected_count} loaded={loaded_rejected_count}"
            )

        loaded_processed_count = load_processed_data(
            valid_df, processed_path, source_file_hash
        )

        if loaded_processed_count != validated_count:
            raise ValueError(
                f"Processed row persistence mismatch: "
                f"expected={validated_count} loaded={loaded_processed_count}"
            )

        return {
            "read": read,
            "duplicated": duplicates_dropped,
            "rejected": rejected_count,
            "skipped": skipped,
            "loaded": loaded,
            "elapsed": elapsed,
        }

    except KeyError, ValueError, TypeError:
        logger.exception("Pipeline encountered an error")

        raise

    except psycopg.OperationalError:
        logger.exception("Database connection/operation failed")

        raise

    except psycopg.DataError:
        logger.exception("Database rejected the data")

        raise

    except psycopg.Error:
        logger.exception("Miscellaneous database error")

        raise
