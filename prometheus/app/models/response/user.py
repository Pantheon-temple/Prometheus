from pydantic import BaseModel


class UserResponse(BaseModel):
    """
    Response model for a user.
    """

    model_config = {
        "from_attributes": True,
    }

    id: int
    username: str
    email: str
    issue_credit: int
    is_superuser: bool
