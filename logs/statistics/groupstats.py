from collections import Counter

from typing import Optional, Dict
from logs.statistics.ipsatats import Ip_stats
from logs.statistics.helpers import IJSONSerialize


class Group_stats(IJSONSerialize):
    """Data structure to store statistical informations about one category
    of entries (either bots or people).
    Implements IJSONSerialize

    Attributes
    ----------
    stats: Dict[str, Iip_stats]
        maps IPv4 as string to Iip_stats object
        which stores information regarding the IPv4
    day_req_distrib: List[int]
        list of length 24,
        i-th element represnts the sum of request
        between i:00 to i+1:00 o'clock
    day_sess_distrib: List[int]
        list of length 24,
        i-th element represnts the sum of sessions
        between i:00 to i+1:00 o'clock
    week_req_distrib: List[int]
        list of length 7,
        i-th element represnts the sum of request
        in i-th day of week,
        Monday is 0 and Sunday is 6
    week_sess_distrib: List[int]
        list of length 7,
        i-th element represnts the sum of sessions
        in i-th day of week.
        Monday is 0 and Sunday is 6
    month_req_distrib: Counter[Tuple[int, int], int]
        maps tuples (<year>, <month>) to the sum
        of requests in the month
    month_sess_distrib: Counter[Tuple[int, int], int]
        maps tuples (<year>, <month>) to the sum
        of sessions in the month
    """

    __slots__ = (
        "stats",
        "day_req_distrib",
        "week_req_distrib",
        "month_req_distrib",
        "day_sess_distrib",
        "week_sess_distrib",
        "month_sess_distrib",
    )

    def __init__(self, js: Optional[Dict] = None):
        if js is not None:
            self.from_json(js)
            return

        self.stats: Dict[str, Ip_stats] = {}
        self.day_req_distrib = [0] * 24
        self.day_sess_distrib = [0] * 24
        self.week_req_distrib = [0] * 7
        self.week_sess_distrib = [0] * 7
        self.month_req_distrib = Counter()
        self.month_sess_distrib = Counter()

    def _set_attr(self, name, data):
        if name == "stats":
            self.stats = {key: Ip_stats(None, json=stat) for key, stat in data.items()}
        elif name == "month_req_distrib":
            self.month_req_distrib = Counter(
                {tuple(map(int, key.split(","))): val for key, val in data.items()}
            )
        elif name == "month_sess_distrib":
            self.month_sess_distrib = Counter(
                {tuple(map(int, key.split(","))): val for key, val in data.items()}
            )
        else:
            setattr(self, name, data)

    def _get_attr(self, name: str):
        if name == "stats":
            return {key: stat.json() for key, stat in self.stats.items()}
        if name == "month_req_distrib":
            return {
                f"{key[0]},{key[1]}": val for key, val in self.month_req_distrib.items()
            }
        if name == "month_sess_distrib":
            return {
                f"{key[0]},{key[1]}": val
                for key, val in self.month_sess_distrib.items()
            }

        return getattr(self, name, None)
