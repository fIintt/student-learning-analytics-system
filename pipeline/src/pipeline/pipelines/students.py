from functools import partial
import logging
from pathlib import Path

from pipeline.loading.postgres import fetch_program_ids, load_students
from pipeline.logging_config import PipelineLogs
from pipeline.pipelines.runner import run_pipeline
from pipeline.transformation.students import transform_students
from pipeline.validation.students import validate_students
import psycopg

from pipeline.config import RAW_STUDENTS_PATH, REJECTED_STUDENTS_PATH

logger = logging.getLogger(__name__)


def run_student_pipeline(
    conn: psycopg.Connection,
    path: Path = RAW_STUDENTS_PATH,
) -> PipelineLogs:
    program_ids = fetch_program_ids(conn)

    if not program_ids:
        logger.warning("Programs table is empty")

    return run_pipeline(
        name="students",
        conn=conn,
        path=path,
        rejected_path=REJECTED_STUDENTS_PATH,
        transform=transform_students,
        validate=partial(validate_students, valid_program_ids=program_ids),
        load=load_students,
    )
