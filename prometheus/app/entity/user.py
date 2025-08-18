from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int = Field(primary_key=True, description="User ID")

    username: str = Field(
        index=True, unique=True, max_length=20, description="Username of the user"
    )
    email: str = Field(
        index=True, unique=True, max_length=30, description="Email address of the user"
    )
    password_hash: str = Field(max_length=128, description="Hashed password of the user")

    github_token: str = Field(
        default=None,
        nullable=True,
        description="Optional GitHub token for integrations",
        max_length=100,
    )

    issue_credit: int = Field(default=0, ge=0, description="Number of issue credits the user has")
    is_superuser: bool = Field(default=False, description="Whether the user is a superuser")
