from prometheus.exceptions.server_exception import ServerException


class JWTException(ServerException):
    """
    class for JWT exceptions.
    This exception is raised when there is an issue with JWT operations,
    such as token generation or validation.
    """

    def __init__(self, code: int = 401, message: str = "An error occurred with the JWT operation."):
        super().__init__(code, message)
