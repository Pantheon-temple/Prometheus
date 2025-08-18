from fastapi import APIRouter

from prometheus.app.api.routes import auth, issue, repository
from prometheus.configuration.config import settings

api_router = APIRouter()
api_router.include_router(repository.router, prefix="/repository", tags=["repository"])
api_router.include_router(issue.router, prefix="/issue", tags=["issue"])

if settings.ENABLE_AUTHENTICATION:
    api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
