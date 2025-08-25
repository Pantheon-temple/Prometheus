import re

from pydantic import BaseModel, Field, field_validator, model_validator


class LoginRequest(BaseModel):
    username: str = Field(description="username of the user", max_length=20)
    email: str = Field(
        description="email of the user",
        examples=["your_email@gmail.com"],
        max_length=30,
    )
    password: str = Field(
        description="password of the user",
        examples=["P@ssw0rd!"],
        min_length=8,
        max_length=30,
    )

    @field_validator("email", mode="after")
    def validate_email_format(cls, v: str) -> str:
        # Allow empty email
        if not v:
            return v

        # Simple regex for email validation
        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v

    @model_validator(mode="after")
    def check_username_or_email(self) -> "LoginRequest":
        if not self.username and not self.email:
            raise ValueError("At least one of 'username' or 'email' must be provided.")
        return self


class CreateUserRequest(BaseModel):
    username: str = Field(description="username of the user", max_length=20)
    email: str = Field(
        description="email of the user",
        examples=["your_email@gmail.com"],
        max_length=30,
    )
    password: str = Field(
        description="password of the user",
        examples=["P@ssw0rd!"],
        min_length=8,
        max_length=30,
    )
    invitation_code: str = Field(
        description="invitation code for registration",
        examples=["abcd-efgh-ijkl-mnop"],
        max_length=36,
        min_length=36,
    )

    @field_validator("email", mode="after")
    def validate_email_format(cls, v: str) -> str:
        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v
