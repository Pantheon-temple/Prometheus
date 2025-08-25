from fastapi import APIRouter, Request

from prometheus.app.models.requests.auth import CreateUserRequest, LoginRequest
from prometheus.app.models.response.auth import LoginResponse
from prometheus.app.models.response.response import Response
from prometheus.app.services.invitation_code_service import InvitationCodeService
from prometheus.app.services.user_service import UserService
from prometheus.configuration.config import settings
from prometheus.exceptions.server_exception import ServerException

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


@router.post(
    "/register/",
    summary="Register a new user",
    description="Register a new user with username, email, password and invitation code.",
    response_description="Returns a success message upon successful registration",
    response_model=Response,
)
def register(request: Request, create_user_request: CreateUserRequest) -> Response:
    """
    Register a new user with username, email, password and invitation code.
    Returns a success message upon successful registration.
    """
    invitation_code_service: InvitationCodeService = request.app.state.service[
        "invitation_code_service"
    ]
    user_service: UserService = request.app.state.service["user_service"]

    # Check if the invitation code is valid
    if not invitation_code_service.check_invitation_code(create_user_request.invitation_code):
        raise ServerException(code=400, message="Invalid or expired invitation code")

    # Create the user
    user_service.create_user(
        username=create_user_request.username,
        email=create_user_request.email,
        password=create_user_request.password,
        issue_credit=settings.DEFAULT_USER_ISSUE_CREDIT,
    )

    # Mark the invitation code as used
    invitation_code_service.mark_code_as_used(create_user_request.invitation_code)

    return Response(message="User registered successfully")
