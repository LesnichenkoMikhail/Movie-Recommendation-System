import functools

from api.services import ensure_user


def require_user(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ensure_user(kwargs["db"], kwargs["user_id"])
        return func(*args, **kwargs)

    return wrapper
