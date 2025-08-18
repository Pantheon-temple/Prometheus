from fastapi import APIRouter, Request

from prometheus.app.models.requests.auth import LoginRequest
from prometheus.app.models.response.auth import LoginResponse
from prometheus.app.models.response.response import Response
from prometheus.app.services.user_service import UserService

router = APIRouter()


@router.post(
    "/login/",
    summary="Login to the system",
    description="Login to the system using username, email, and password. Returns an access token.",
    response_description="Returns an access token for authenticated requests",
    response_model=Response[LoginResponse],
)
def login(login_request: LoginRequest, request: Request) -> Response[LoginResponse]:
    """
    Login to the system using username, email, and password.
    Returns an access token for authenticated requests.
    """

    user_service: UserService = request.app.state.service["user_service"]
    access_token = user_service.login(
        username=login_request.username,
        email=login_request.email,
        password=login_request.password,
    )
    return Response(data=LoginResponse(access_token=access_token))
