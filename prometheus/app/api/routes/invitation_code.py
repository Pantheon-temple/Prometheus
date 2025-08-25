from typing import Sequence

from fastapi import APIRouter, Request

from prometheus.app.decorators.require_login import requireLogin
from prometheus.app.entity.invitation_code import InvitationCode
from prometheus.app.models.response.response import Response
from prometheus.app.services.user_service import UserService
from prometheus.configuration.config import settings
from prometheus.exceptions.server_exception import ServerException

router = APIRouter()


@router.post(
    "/create/",
    summary="Create a new invitation code",
    description="Generates a new invitation code for user registration.",
    response_description="Returns the newly created invitation code",
    response_model=Response[InvitationCode],
)
@requireLogin
def create_invitation_code(request: Request) -> Response[InvitationCode]:
    """
    Create a new invitation code.
    """
    # Check if the user is an admin
    user_service: UserService = request.app.state.service["user_service"]
    if settings.ENABLE_AUTHENTICATION and not user_service.is_admin(request.state.user_id):
        raise ServerException(code=403, message="Only admins can create invitation codes")

    # Create a new invitation code
    invitation_code_service = request.app.state.service["invitation_code_service"]
    invitation_code = invitation_code_service.create_invitation_code()
    return Response(data=invitation_code)


@router.get(
    "/list/",
    summary="List all invitation codes",
    description="Retrieves a list of all invitation codes.",
    response_description="Returns a list of invitation codes",
    response_model=Response[Sequence[InvitationCode]],
)
@requireLogin
def list_invitation_codes(request: Request) -> Response[Sequence[InvitationCode]]:
    """
    List all invitation codes.
    """
    # Check if the user is an admin
    user_service: UserService = request.app.state.service["user_service"]
    if settings.ENABLE_AUTHENTICATION and not user_service.is_admin(request.state.user_id):
        raise ServerException(code=403, message="Only admins can list invitation codes")

    # List all invitation codes
    invitation_code_service = request.app.state.service["invitation_code_service"]
    invitation_codes = invitation_code_service.list_invitation_codes()
    return Response(data=invitation_codes)
