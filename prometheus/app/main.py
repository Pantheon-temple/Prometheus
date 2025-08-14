from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from prometheus.app import dependencies
from prometheus.app.api import issue, repository
from prometheus.utils.logger_manager import get_logger

# 获取应用程序的logger
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialization on startup
    app.state.service_coordinator = dependencies.initialize_services()
    # Initialization Completed
    yield
    # Cleanup on shutdown
    app.state.service_coordinator.clear()
    app.state.service_coordinator.close()


app = FastAPI(lifespan=lifespan)

app.include_router(repository.router, prefix="/repository", tags=["repository"])
app.include_router(issue.router, prefix="/issue", tags=["issue"])


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
