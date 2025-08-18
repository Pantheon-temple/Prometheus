import re

from pydantic import BaseModel, Field, field_validator


class UploadRepositoryRequest(BaseModel):
    https_url: str = Field(description="The URL of the repository", max_length=100)
    commit_id: str | None = Field(
        default=None,
        description="The commit id of the repository, "
        "if not provided, the latest commit in the main branch will be used.",
        min_length=40,
        max_length=40,
    )
    github_token: str | None = Field(
        default=None,
        description="Optional GitHub token for repository clone",
        max_length=100,
    )


class CreateBranchAndPushRequest(BaseModel):
    repository_id: int = Field(
        description="The ID of the repository this branch belongs to.", examples=[1]
    )
    patch: str = Field(
        description="The patch to apply to the repository", examples=["diff --git a/foo.c b/foo.c"]
    )
    branch_name: str = Field(
        description="The name of the branch to create", examples=["feature/new-feature"]
    )
    commit_message: str = Field(
        description="The commit message for the changes", examples=["Add new feature"]
    )

    @field_validator("branch_name", mode="after")
    def validate_branch_name_format(cls, name: str) -> str:
        """
        Check if a branch name is valid according to Git's rules.
        Reference: https://git-scm.com/docs/git-check-ref-format
        """
        if not name or name in (".", "..") or name.strip() != name:
            raise ValueError(
                f"Invalid branch name '{name}': name cannot be empty, "
                f"'.' or '..', and cannot have leading/trailing spaces."
            )

        # Cannot start or end with '/'
        if name.startswith("/") or name.endswith("/"):
            raise ValueError(
                f"Invalid branch name '{name}': branch name cannot start or end with '/'. Example: 'feature/new'."
            )

        # Cannot contain consecutive slashes
        if "//" in name:
            raise ValueError(
                f"Invalid branch name '{name}': branch name cannot contain consecutive slashes '//'."
            )

        # Cannot contain ASCII control characters or space
        if re.search(r"[\000-\037\177\s]", name):
            raise ValueError(
                f"Invalid branch name '{name}': branch name cannot contain spaces or control characters. "
                f"Use '-' or '_' instead of spaces."
            )

        # Cannot end with .lock
        if name.endswith(".lock"):
            raise ValueError(f"Invalid branch name '{name}': branch name cannot end with '.lock'.")

        # Cannot contain these special sequences
        forbidden = ["@", "\\", "?", "[", "~", "^", ":", "*", "..", "@{"]
        for token in forbidden:
            if token in name:
                raise ValueError(
                    f"Invalid branch name '{name}': contains forbidden sequence or character {token}. "
                    f"Avoid '@', '?', '*', '..', '@{{', etc."
                )

        return name
