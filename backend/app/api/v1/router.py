from fastapi import APIRouter

from app.api.v1 import auth, catalog, followups, metric_definitions, metrics, reports, review, support_cases

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(metric_definitions.router)
api_router.include_router(metrics.router)
api_router.include_router(review.router)
api_router.include_router(support_cases.router)
api_router.include_router(followups.router)
api_router.include_router(reports.router)
