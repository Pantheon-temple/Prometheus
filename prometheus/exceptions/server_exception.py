class ServerException(Exception):
    """
    Base class for server exceptions.
    This exception is raised when there is an issue with server operations.
    """

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
