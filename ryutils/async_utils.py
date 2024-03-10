import asyncio
import functools
import queue
import threading
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


WorkerCallback = T.Callable[..., None]


class Worker(threading.Thread):
    """
    Worker thread class

    This module provides a class for creating a worker thread that utilizes
    Queue.Queue to process messages.
    """

    def __init__(
        self,
        queue_input: queue.Queue,
        process_callback: WorkerCallback,
        *args: T.Any,
        **kwargs: T.Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.queue = queue_input
        self.process = process_callback

    def run(self) -> None:
        """Run the worker thread"""
        while True:
            item = self.queue.get()
            if item is None:  # Use a sentinel value to break the loop
                self.queue.task_done()
                break
            self.process(**item)  # type: ignore
            self.queue.task_done()
