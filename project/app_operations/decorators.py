from django.db import connection
from functools import wraps


def with_connection_usable(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        try:
            connection.connection.ping()
        except:
            connection.close()
        return func(*args, **kwargs)

    return decorator