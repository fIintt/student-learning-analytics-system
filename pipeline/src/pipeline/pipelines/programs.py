from pathlib import Path

from pipeline.loading.postgres import load_programs
from pipeline.logging_config import PipelineLogs
from pipeline.pipelines.runner import run_pipeline
from pipeline.transformation.programs import transform_programs
from pipeline.validation.programs import validate_programs
import psycopg

from pipeline.config import (
    RAW_PROGRAMS_PATH,
    REJECTED_PROGRAMS_PATH,
)


def run_program_pipeline(
    conn: psycopg.Connection, path: Path = RAW_PROGRAMS_PATH
) -> PipelineLogs:
    return run_pipeline(
        name="programs",
        conn=conn,
        path=path,
        rejected_path=REJECTED_PROGRAMS_PATH,
        transform=transform_programs,
        validate=validate_programs,
        load=load_programs,
    )
