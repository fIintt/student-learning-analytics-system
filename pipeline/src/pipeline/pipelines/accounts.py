from pathlib import Path

from pipeline.loading.postgres import load_accounts
from pipeline.logging_config import PipelineLogs
from pipeline.pipelines.runner import run_pipeline
from pipeline.transformation.accounts import transform_accounts
from pipeline.validation.accounts import validate_accounts
import psycopg

from pipeline.config import (
    PROCESSED_ACCOUNT_PATH,
    RAW_ACCOUNT_PATH,
    REJECTED_ACCOUNT_PATH,
)


def run_account_pipeline(
    conn: psycopg.Connection, path: Path = RAW_ACCOUNT_PATH
) -> PipelineLogs:
    return run_pipeline(
        name="accounts",
        conn=conn,
        path=path,
        rejected_path=REJECTED_ACCOUNT_PATH,
        processed_path=PROCESSED_ACCOUNT_PATH,
        transform=transform_accounts,
        validate=validate_accounts,
        load=load_accounts,
    )
