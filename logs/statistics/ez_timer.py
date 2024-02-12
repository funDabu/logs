
import sys
import time
from typing import Optional

class Ez_timer:
    __slots__ = ("name", "time")

    def __init__(self, name: str, start=True, verbose=True):
        self.name = name
        self.time = None
        if start:
            self.start(verbose)

    def start(self, verbose=True) -> float:
        self.time = time.time()
        if verbose:
            print(f'{self.name.capitalize()} has started.', file=sys.stderr)

    def finish(self, verbose=True) -> Optional[float]:
        if self.time is None:
            return

        time_diff = time.time() - self.time
        if verbose:
            print(f'{self.name} has finished, took {round(time_diff)} seconds.',
                  file=sys.stderr)
        return time_diff
