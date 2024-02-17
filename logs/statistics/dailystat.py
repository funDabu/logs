from typing import Set, NamedTuple
import datetime


class Daily_stats(NamedTuple):
    """Data structure to strore information for single day
    Attribures
    ----------
    date: str
    ips: Set[str]
    requests: int
    sessions: int
    """
    date: datetime.date
    ips: Set[str]
    requests: int
    sessions: int