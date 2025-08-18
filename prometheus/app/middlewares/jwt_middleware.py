from typing import Set, Tuple

from fastapi import FastAPI, Request
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from prometheus.exceptions.jwt_exception import JWTException
from prometheus.utils.jwt_utils import JWTUtils


class JWTMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, login_required_routes: Set[Tuple[str, str]]):
        super().__init__(app)
        self.jwt_utils = JWTUtils()  # Initialize the JWT utility
        self.login_required_routes = (
            login_required_routes  # List of paths to exclude from JWT validation
        )

    async def dispatch(self, request: Request, call_next):
        # Allow OPTIONS requests to pass through without authentication (for CORS preflight)
        if request.method == "OPTIONS":
            response = await call_next(request)
            return response

        # Check if the request path is in excluded paths
        path = request.url.path
        if (request.method, path) not in self.login_required_routes:
            # Proceed to the next middleware or route handler if the path is excluded
            response = await call_next(request)
            return response

        # Retrieve the Authorization header from the request
        authorization: str = request.headers.get("Authorization")
        # Extract the scheme (e.g., "Bearer") and the token from the header
        scheme, token = get_authorization_scheme_param(authorization)

        # Check if authorization header is missing or incorrect scheme
        if not authorization or scheme.lower() != "bearer":
            return JSONResponse(
                status_code=401,
                content={"code": 401, "message": "Valid JWT Token is missing", "data": None},
            )

        try:
            # Attempt to decode and validate the JWT token
            payload = self.jwt_utils.decode_token(token)
        except JWTException as e:
            # If token validation fails, return an error response with details
            return JSONResponse(
                status_code=e.code,
                content={"code": e.code, "message": e.message, "data": None},
            )
        request.state.user_id = payload.get("user_id", None)
        # Proceed to the next middleware or route handler if validation succeeds
        response = await call_next(request)
        return response
