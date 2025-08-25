from datetime import datetime, timedelta, timezone

from sqlmodel import Field, SQLModel

from prometheus.configuration.config import settings


class InvitationCode(SQLModel, table=True):
    """
    InvitationCode model for managing invitation codes.
    """

    id: int = Field(primary_key=True, description="ID")
    code: str = Field(index=True, unique=True, max_length=36, description="Invitation code")
    is_used: bool = Field(default=False, description="Whether the invitation code has been used")
    expiration_time: datetime = Field(
        default=datetime.now(timezone.utc) + timedelta(days=settings.INVITATION_CODE_EXPIRE_TIME),
        description="Expiration time of the invitation code",
    )
