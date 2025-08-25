from fastapi import APIRouter

from prometheus.app.api.routes import auth, invitation_code, issue, repository, user
from prometheus.configuration.config import settings

api_router = APIRouter()
api_router.include_router(repository.router, prefix="/repository", tags=["repository"])
api_router.include_router(issue.router, prefix="/issue", tags=["issue"])

if settings.ENABLE_AUTHENTICATION:
    api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
    api_router.include_router(
        invitation_code.router, prefix="/invitation-code", tags=["invitation_code"]
    )
    api_router.include_router(user.router, prefix="/user", tags=["user"])
