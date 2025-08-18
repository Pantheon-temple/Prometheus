import inspect
from functools import wraps


def requireLogin(func):
    """
    Decorator to indicate that a route requires user authentication.
    This decorator can be used to mark routes that should only be accessible to authenticated users.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    # Set a custom attribute to indicate that this route requires login
    setattr(wrapper, "_require_login", True)
    return wrapper
