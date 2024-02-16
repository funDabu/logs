from typing import Set, NamedTuple


class Daily_stats(NamedTuple):
    """Data structure to strore information for single day
    Attribures
    ----------
    ips: Set[str]
    requests: int
    sessions: int
    """
    ips: Set[str]
    requests: int
    sessions: int