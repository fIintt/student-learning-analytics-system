# 10/19/2026
import logging

from pipeline.loading.postgres import connect_postgres, create_schemas
from pipeline.logging_config import log_summary, setup_logging
from pipeline.pipelines.programs import run_programs_pipeline
from pipeline.pipelines.students import run_students_pipeline

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()

    logger.info("Starting...")

    try:
        summary = {}

        with connect_postgres() as conn:
            create_schemas(conn)

            summary["programs"] = run_programs_pipeline(conn)
            summary["students"] = run_students_pipeline(conn)

        log_summary(summary)

    except Exception:
        logger.exception("Pipeline failed")

        raise

    logger.info("All pipelines finished")


if __name__ == "__main__":
    main()
