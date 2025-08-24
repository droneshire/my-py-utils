"""
Worker thread class

This module provides a class for creating a worker thread that utilizes
Queue.Queue to process messages.
"""

import queue
import threading
import typing as T

from ryutils import log

WorkerCallback = T.Callable[..., None]


class Worker(threading.Thread):
    """Worker thread class"""

    def __init__(
        self,
        queue_input: queue.Queue,
        process_callback: WorkerCallback,
        *args: T.Any,
        verbose: bool = False,
        **kwargs: T.Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.queue = queue_input
        self.process = process_callback
        self.verbose = verbose

    def run(self) -> None:
        """Run the worker thread"""
        while True:
            item = self.queue.get()
            if item is None:  # Use a sentinel value to break the loop
                self.queue.task_done()
                break
            if self.verbose:
                log.print_normal(f"Processing {item}")
            self.process(**item)
            self.queue.task_done()
