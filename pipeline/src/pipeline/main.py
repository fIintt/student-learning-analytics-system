# 10/19/2026
import logging

from pipeline.loading.postgres import connect_postgres, create_schemas
from pipeline.logging_config import setup_logging
from pipeline.pipelines.programs import run_programs_pipeline
from pipeline.pipelines.students import run_students_pipeline

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()

    try:

        with connect_postgres() as conn:
            create_schemas(conn)

            run_programs_pipeline(conn)
            run_students_pipeline(conn)

    except Exception:
        logger.exception("Pipeline failed")

        raise


if __name__ == "__main__":
    main()
