from typing import Set, NamedTuple
import datetime
from typing import Optional

LOG_FORMAT = "date ips requests sessions"
LOG_DELIM = "\t"


###################
##### CLASSES #####
###################
class DailyStats(NamedTuple):
    """Data structure to strore information for single day
    Attribures
    ----------
    date: datetime.date
    ips: Set[str]
        unique ip addresses
    requests: int
    sessions: int
    """

    date: datetime.date
    ips: Set[str]
    requests: int
    sessions: int


class SimpleDailyStats:
    """Data structure to strore information for single day,
    Attribures
    ----------
    date: datetime.date
    ips: int
        number of unique ip addresses
    requests: int
    sessions: int
    """

    slots = ("date", "ips", "requests", "sessions")

    def __init__(
        self,
        date: datetime.date,
        ips: int,
        requests: int,
        sessions: int,
    ):
        self.date = date
        self.requests = requests
        self.sessions = sessions
        self.ips = ips

    def __iter__(self):
        for slot in self.__class__.slots:
            yield self.__getattribute__(slot)

    def log_format(
        self,
        log_format: Optional[str] = None,
        delim: Optional[str] = None,
    ) -> str:
        log_format = LOG_FORMAT if log_format is None else log_format
        delim = LOG_DELIM if delim is None else delim

        return delim.join(self._attr_to_str(attr) for attr in log_format.split())

    def _attr_to_str(self, attribute_name: str) -> str:
        if attribute_name == "date":
            return self.date.isoformat()

        return str(self.__getattribute__(attribute_name))

    @classmethod
    def from_logcache(
        cls,
        log_entry: str,
        log_format: Optional[str] = None,
        delim: Optional[str] = None,
    ) -> "SimpleDailyStats":
        log_format = LOG_FORMAT if log_format is None else log_format
        delim = LOG_DELIM if delim is None else delim

        attr_val = dict(zip(log_format.split(), log_entry.split(delim)))

        return SimpleDailyStats(
            date=date_from_isoformat(attr_val["date"]),
            ips=int(attr_val["ips"]),
            requests=int(attr_val["requests"]),
            sessions=int(attr_val["sessions"]),
        )

    @classmethod
    def from_daily_stats(cls, daily_stat: DailyStats) -> "SimpleDailyStats":
        return SimpleDailyStats(
            date=daily_stat.date,
            ips=len(daily_stat.ips),
            requests=daily_stat.requests,
            sessions=daily_stat.sessions,
        )


# class SimpleDailyStats(NamedTuple):
#     """Data structure to strore information for single day,
#     Attribures
#     ----------
#     date: datetime.date
#     ips: int
#         number of unique ip addresses
#     requests: int
#     sessions: int
#     """

#     date: datetime.date
#     ips: int
#     requests: int
#     sessions: int


#################
### FUNCTIONS ###
#################


def date_from_isoformat(date_str: str, isoformat: str = "%Y-%m-%d") -> datetime.date:
    """Converts date string in isoformat to datetime.date object"""
    return datetime.datetime.strptime(date_str, isoformat).date()


# def log_format_SimpleDailyStats(
#     daily_stat: SimpleDailyStats,
#     log_format: Optional[str] = None,
#     delim: Optional[str] = None,
# ) -> str:

#     log_format = LOG_FORMAT if log_format is None else log_format
#     delim = LOG_DELIM if delim is None else delim

#     return delim.join(_attr_to_str(daily_stat, attr) for attr in log_format.split())

# def simple_daily_stat_getattr(daily_stat: SimpleDailyStats, attribute_name: str):
#     """Returns given attribute from `daily_stat`.
#     Raises AttributeError

#     Parameters
#     ----------
#     daily_stat: SimpleDailyStats
#     attribute_name: str
#         has to mach exactly one of the attributes of SimpleDailyStats,
#         otherwise reises AttributeError
#     """
#     if attribute_name == "date":
#         return daily_stat.date
#     if attribute_name == "ips":
#         return daily_stat.ips
#     if attribute_name == "requests":
#         return daily_stat.requests
#     if attribute_name == "sessions":
#         return daily_stat.sessions

#     raise AttributeError(
#         "Attribute", attribute_name, "does not exist for an object of type DailyStats"
#     )

# def _attr_to_str(daily_stat: SimpleDailyStats, attribute_name: str) -> str:
#     if attribute_name == "date":
#         return daily_stat.date.isoformat()

#     return str(simple_daily_stat_getattr(daily_stat, attribute_name))
