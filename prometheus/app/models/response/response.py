from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    """
    Generic response model for API responses.
    """

    code: int = 200
    message: str = "success"
    data: T | None = None
