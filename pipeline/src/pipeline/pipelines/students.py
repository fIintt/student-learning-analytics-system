from pathlib import Path

from pipeline.loading.postgres import load_students
from pipeline.logging_config import PipelineLogs
from pipeline.pipelines.runner import run_pipeline
from pipeline.transformation.students import transform_students
from pipeline.validation.students import validate_students
import psycopg

from pipeline.config import RAW_STUDENTS_PATH, REJECTED_STUDENTS_PATH


def run_students_pipeline(
    conn: psycopg.Connection, path: Path = RAW_STUDENTS_PATH
) -> PipelineLogs:
    return run_pipeline(
        name="students",
        conn=conn,
        path=path,
        rejected_path=REJECTED_STUDENTS_PATH,
        transform=transform_students,
        validate=validate_students,
        load=load_students,
    )
