from pathlib import Path

from pipeline.loading.postgres import load_staff
from pipeline.logging_config import PipelineLogs
from pipeline.pipelines.runner import run_pipeline
from pipeline.transformation.staff import transform_staff
from pipeline.validation.staff import validate_staff
import psycopg

from pipeline.config import (
    PROCESSED_STAFF_PATH,
    RAW_STAFF_PATH,
    REJECTED_STAFF_PATH,
)


def run_staff_pipeline(
    conn: psycopg.Connection, path: Path = RAW_STAFF_PATH
) -> PipelineLogs:
    return run_pipeline(
        name="staff",
        conn=conn,
        path=path,
        rejected_path=REJECTED_STAFF_PATH,
        processed_path=PROCESSED_STAFF_PATH,
        transform=transform_staff,
        validate=validate_staff,
        load=load_staff,
    )
