from pydantic import BaseModel


class LoginResponse(BaseModel):
    """
    Response model for user login.
    """

    access_token: str
