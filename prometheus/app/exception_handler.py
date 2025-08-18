from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from prometheus.exceptions.server_exception import ServerException


def register_exception_handlers(app: FastAPI):
    """Global exception handlers for the FastAPI application."""

    @app.exception_handler(ServerException)
    async def custom_exception_handler(_request: Request, exc: ServerException):
        """
        Custom exception handler for ServerException.
        """
        return JSONResponse(
            status_code=exc.code, content={"code": exc.code, "message": exc.message, "data": None}
        )
