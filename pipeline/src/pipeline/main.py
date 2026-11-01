# 10/19/2026
import logging

from pipeline.loading.postgres import connect_postgres, create_schemas
from pipeline.logging_config import log_summary, setup_logging
from pipeline.pipelines.academic_performance import run_academic_performance_pipeline
from pipeline.pipelines.programs import run_program_pipeline
from pipeline.pipelines.students import run_student_pipeline

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()

    logger.info("Starting...")

    summary = {}

    with connect_postgres() as conn:
        create_schemas(conn)

        summary["programs"] = run_program_pipeline(conn)
        summary["students"] = run_student_pipeline(conn)
        summary["academic_performance"] = run_academic_performance_pipeline(conn)

    log_summary(summary)

    logger.info("All pipelines finished")


if __name__ == "__main__":
    main()
