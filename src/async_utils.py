import asyncio
import functools
import typing as T


def force_sync(function_handle: T.Callable) -> T.Callable:
    """Force a function to run synchronously."""

    @functools.wraps(function_handle)
    def wrapper(*args: T.Any, **kwargs: T.Any) -> T.Any:
        response = function_handle(*args, **kwargs)
        if asyncio.iscoroutine(response):
            return asyncio.get_event_loop().run_until_complete(response)
        return response

    return wrapper
