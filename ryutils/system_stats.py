import time
import typing as T
from functools import wraps

import psutil
from memory_profiler import memory_usage

from ryutils.path_util import get_backtrace_file_name


class ResourceProfiler:
    cpu_before: float
    cpu_after: float
    mem_before: float
    mem_after: float
    start_time: float
    end_time: float

    def __init__(
        self,
        id_string: str,
        start_time: float,
        end_time: float,
        cpu_before: float,
        cpu_after: float,
        mem_before: float,
        mem_after: float,
    ) -> None:
        self.id_string = id_string
        self.start_time = start_time
        self.end_time = end_time
        self.cpu_before = cpu_before
        self.cpu_after = cpu_after
        self.mem_before = mem_before
        self.mem_after = mem_after

    def __str__(self) -> str:
        return (
            f"Function `{self.id_string}` executed in "
            f"{self.end_time - self.start_time:.4f} seconds\n"
            f"CPU usage before: {self.cpu_before}%, after: {self.cpu_after}%, "
            f"difference: {self.cpu_after - self.cpu_before}%"
            f"Memory usage before: {self.mem_before} MB, after: {self.mem_after} MB, "
            f"difference: {self.mem_after - self.mem_before} MB"
        )

    def __repr__(self) -> str:
        return (
            f"ResourceProfiler(id_string={self.id_string}, start_time={self.start_time}, "
            f"end_time={self.end_time}, cpu_before={self.cpu_before}, cpu_after={self.cpu_after},"
            f" mem_before={self.mem_before}, mem_after={self.mem_after})"
        )


def resource_profiler(
    print_resource_stats: bool = False,
    resource_callback_func: T.Optional[T.Callable[[ResourceProfiler], None]] = None,
) -> T.Callable:
    """
    This decorator tracks resource usage (CPU and memory) of a function execution.

    Example usage:

    @resource_profiler()
    def example_function():
        # Function implementation
        pass

    @resource_profiler(print_resource_stats=True, resource_callback_func=lambda x: print(x))
    def example_method():
        # Method implementation
        pass
    """

    def decorator(func: T.Callable) -> T.Callable:
        @wraps(func)
        def wrapper(*args: T.Any, **kwargs: T.Any) -> T.Any:
            # Record initial stats
            cpu_before = psutil.cpu_percent(interval=1)
            mem_before = memory_usage()[0]

            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()

            # Record final stats
            cpu_after = psutil.cpu_percent(interval=1)
            mem_after = memory_usage()[0]

            file_name = get_backtrace_file_name(frame=2)
            id_string = f"{file_name}:{func.__name__}()"

            resource_profiler_obj = ResourceProfiler(
                id_string, start_time, end_time, cpu_before, cpu_after, mem_before, mem_after
            )
            if print_resource_stats:
                print(resource_profiler_obj)

            if resource_callback_func:
                resource_callback_func(resource_profiler_obj)

            return result

        return wrapper

    return decorator
