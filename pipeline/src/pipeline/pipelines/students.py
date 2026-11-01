import logging
from pathlib import Path
import time

from pipeline.ingestion.extract import extract_csv
from pipeline.loading.parquet import load_rejected_data
from pipeline.loading.postgres import load_students
from pipeline.transformation.students import transform_students
from pipeline.utils import hash_file
from pipeline.validation.students import validate_students
import polars as pl
import psycopg

from pipeline.config import RAW_STUDENTS_PATH, REJECTED_STUDENTS_PATH

logger = logging.getLogger(__name__)


def run_students_pipeline(
    conn: psycopg.Connection, path: Path = RAW_STUDENTS_PATH
) -> None:
    started_at = time.perf_counter()

    logger.info("Pipeline started")

    try:
        source_file_hash = hash_file(path)

        raw = extract_csv(path)
        transformed = transform_students(raw)
        validated, rejected = validate_students(transformed)

        read_df, deduped_df, valid_df, rejected_df = pl.collect_all(
            [raw.select(pl.len()), transformed.select(pl.len()), validated, rejected]
        )

        read = read_df.item()
        duplicates_dropped = read - deduped_df.item()
        valid = valid_df.height
        rejected_count = rejected_df.height

        if read != duplicates_dropped + rejected_count + valid:
            raise ValueError(
                f"Counts do not add up: read={read} duplicates={duplicates_dropped} "
                f"rejected={rejected_count} valid={valid}"
            )

        loaded_rejected_count = load_rejected_data(
            rejected_df, REJECTED_STUDENTS_PATH, source_file_hash
        )

        if loaded_rejected_count != rejected_count:
            raise ValueError(
                f"Rejected row persistence mismatch: "
                f"expected={rejected_count} "
                f"loaded={loaded_rejected_count}"
            )

        loaded = load_students(conn, valid_df)

        skipped = valid - loaded

        logger.info(
            "read=%d duplicates_dropped=%d rejected=%d skipped=%d loaded=%d",
            read,
            duplicates_dropped,
            rejected_count,
            skipped,
            loaded,
        )

    except KeyError, ValueError, TypeError:
        logger.exception("Pipeline failed")
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

    else:
        logger.info("Pipeline succeeded")

    finally:
        elapsed = time.perf_counter() - started_at
        logger.info("Elapsed - %.2f seconds", elapsed)
