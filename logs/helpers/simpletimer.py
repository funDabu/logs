import time
from typing import Optional


class SimpleTimer:
    __slots__ = ("state", "start_time", "finish_time")
    STATES = ("unbegun", "running", "finished")

    def __init__(self, start=True):
        self.state = "unbegun"
        self.start_time = None
        self.finish_time = None

        if start:
            self.start()

    def start(self) -> bool:
        if self.state != "unbegun":
            return False
        else:
            self.start_time = time.time()
            self.state = "running"
            return True

    def finish(self) -> bool:
        if self.state != "running":
            return False
        else:
            self.finish_time = time.time()
            self.state = "finished"
            return True
    
    def duration(self) -> Optional[float]:
        if self.state == "finished":
            return self.finish_time - self.start_time
