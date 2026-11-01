from functools import partial
import logging
from pathlib import Path

from pipeline.loading.postgres import fetch_student_ids, load_academic_performance
from pipeline.logging_config import PipelineLogs
from pipeline.pipelines.runner import run_pipeline
from pipeline.transformation.academic_performance import transform_academic_performance
from pipeline.validation.academic_performance import validate_academic_performance
import psycopg

from pipeline.config import (
    RAW_ACADEMIC_PERFORMANCE_PATH,
    REJECTED_ACADEMIC_PERFORMANCE_PATH,
)

logger = logging.getLogger(__name__)


def run_academic_performance_pipeline(
    conn: psycopg.Connection, path: Path = RAW_ACADEMIC_PERFORMANCE_PATH
) -> PipelineLogs:
    student_ids = fetch_student_ids(conn)

    if not student_ids:
        logger.warning("Students table is empty")

    return run_pipeline(
        name="academic_performance",
        conn=conn,
        path=path,
        rejected_path=REJECTED_ACADEMIC_PERFORMANCE_PATH,
        transform=transform_academic_performance,
        validate=partial(validate_academic_performance, valid_student_ids=student_ids),
        load=load_academic_performance,
    )
