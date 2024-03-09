import time
from typing import Dict, Optional, TextIO
from logs.helpers.simpletimer import SimpleTimer


class SimpleLogger:
    """Class used for logging tasks into `log_fd`"""

    def __init__(self, log_fd: Optional[TextIO] = None):
        self.log_fd = log_fd
        self.tasks: Dict[str, SimpleTimer] = {}

    def addTask(self, task_name: str, start: bool = True, verbose: bool = True):
        self.tasks[task_name] = SimpleTimer(start=False)
        if start:
            self.startTask(task_name, verbose=verbose)

    def startTask(self, task_name: str, verbose: bool = True):
        if task_name not in self.tasks:
            raise ValueError("task with name `task_name` not found")

        started = self.tasks[task_name].start()

        if started and verbose and self.log_fd is not None:
            print(f"Task '{task_name}' has started.", file=self.log_fd)

    def finishTask(self, task_name: str, verbose: bool = True) -> Optional[float]:
        if task_name not in self.tasks:
            raise ValueError("task with name `task_name` not found")

        task = self.tasks[task_name]
        finished = task.finish()
        if finished and verbose and self.log_fd is not None:
            print(
                f"Task '{task_name}' has finished, duration: {round(task.duration(), 2)} seconds",
                file=self.log_fd,
            )

    def logMessage(self, message: str, time_stamp: bool = False):
        ts_string = ""
        if time_stamp:
            ts_string = ", at timestamp: " + str(round(time.time(), 2))

        if self.log_fd is not None:
            print(message + ts_string, file=self.log_fd)
