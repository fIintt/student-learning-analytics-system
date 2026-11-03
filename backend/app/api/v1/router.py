from fastapi import APIRouter

from app.api.v1 import (
    academic_imports,
    auth,
    catalog,
    followups,
    health,
    metric_definitions,
    metrics,
    reports,
    review,
    student_portal,
    support_cases,
    teachers,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(metric_definitions.router)
api_router.include_router(metrics.router)
api_router.include_router(review.router)
api_router.include_router(support_cases.router)
api_router.include_router(followups.router)
api_router.include_router(reports.router)
api_router.include_router(academic_imports.router)
api_router.include_router(student_portal.router)

api_router.include_router(teachers.router)
