import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from prometheus.app import dependencies
from prometheus.app.api.main import api_router
from prometheus.app.exception_handler import register_exception_handlers
from prometheus.app.middlewares.jwt_middleware import JWTMiddleware
from prometheus.app.register_login_required_routes import (
    login_required_routes,
    register_login_required_routes,
)
from prometheus.configuration.config import settings

# Create a logger for the application's namespace
logger = logging.getLogger("prometheus")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(getattr(logging, settings.LOGGING_LEVEL))
logger.propagate = False

# Log the configuration settings
logger.info(f"LOGGING_LEVEL={settings.LOGGING_LEVEL}")
logger.info(f"ENVIRONMENT={settings.ENVIRONMENT}")
logger.info(f"BACKEND_CORS_ORIGINS={settings.BACKEND_CORS_ORIGINS}")
logger.info(f"ADVANCED_MODEL={settings.ADVANCED_MODEL}")
logger.info(f"BASE_MODEL={settings.BASE_MODEL}")
logger.info(f"NEO4J_BATCH_SIZE={settings.NEO4J_BATCH_SIZE}")
logger.info(f"WORKING_DIRECTORY={settings.WORKING_DIRECTORY}")
logger.info(f"KNOWLEDGE_GRAPH_MAX_AST_DEPTH={settings.KNOWLEDGE_GRAPH_MAX_AST_DEPTH}")
logger.info(f"KNOWLEDGE_GRAPH_CHUNK_SIZE={settings.KNOWLEDGE_GRAPH_CHUNK_SIZE}")
logger.info(f"KNOWLEDGE_GRAPH_CHUNK_OVERLAP={settings.KNOWLEDGE_GRAPH_CHUNK_OVERLAP}")
logger.info(f"MAX_TOKEN_PER_NEO4J_RESULT={settings.MAX_TOKEN_PER_NEO4J_RESULT}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialization on startup
    app.state.service = dependencies.initialize_services()
    logger.info("Starting services...")
    for service in app.state.service.values():
        service.start()
    # Initialization Completed
    yield
    # Cleanup on shutdown
    logger.info("Shutting down services...")
    for service in app.state.service.values():
        service.close()


def custom_generate_unique_id(route: APIRoute) -> str:
    """
    Custom function to generate unique IDs for API routes based on their tags and names.
    """
    return f"{route.tags[0]}-{route.name}"


app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,  # Title on generated documentation
    openapi_url=f"{settings.BASE_URL}/openapi.json",  # Path to generated OpenAPI documentation
    generate_unique_id_function=custom_generate_unique_id,  # Custom function for generating unique route IDs
    version=settings.version,  # Version of the API
    debug=True if settings.ENVIRONMENT == "local" else False,
)

# Register middlewares
if settings.ENABLE_AUTHENTICATION:
    app.add_middleware(
        JWTMiddleware,
        login_required_routes=login_required_routes,
    )
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API router with a prefix
app.include_router(api_router, prefix=settings.BASE_URL)

# Register the exception handlers
register_exception_handlers(app)
# Register the login-required routes
register_login_required_routes(app)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
