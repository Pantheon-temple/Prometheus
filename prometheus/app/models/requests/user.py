import re

from pydantic import BaseModel, Field, field_validator


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
        min_length=12,
        max_length=30,
    )
    github_token: str = Field(description="github token of the user", max_length=100)

    @field_validator("email", mode="after")
    def validate_email_format(self, v: str) -> str:
        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v
