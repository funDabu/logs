from typing import Set, NamedTuple
import datetime
from logs.statistics.helpers import date_from_isoformat
from typing import Optional

LOG_FORMAT = "date ips requests sessions"
LOG_DELIM = '\t'


class Daily_stats(NamedTuple):
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


class Simple_daily_stats(NamedTuple):
    """Data structure to strore information for single day,
    Attribures
    ----------
    date: datetime.date
    ips: int
        number of unique ip addresses
    requests: int
    sessions: int
    """

    date: datetime.date
    ips: int
    requests: int
    sessions: int


def daily_stats_to_simple(daily_stat: Daily_stats) -> Simple_daily_stats:
    return Simple_daily_stats(
        date=daily_stat.date,
        ips=len(daily_stat.ips),
        requests=daily_stat.requests,
        sessions=daily_stat.sessions,
    )


def log_format_simple_daily_stats(
    daily_stat: Simple_daily_stats,
    log_format: Optional[str] = None,
    delim: Optional[str] = None,
) -> str:
    
    log_format = LOG_FORMAT if log_format is None else log_format
    delim = LOG_DELIM if delim is None else delim

    return delim.join(_attr_to_str(daily_stat, attr) for attr in log_format.split())

def simple_daily_stat_getattr(daily_stat: Simple_daily_stats, attribute_name: str):
    """Returns given attribute from `daily_stat`.
    Raises AttributeError
    
    Parameters
    ----------
    daily_stat: Simple_daily_stats
    attribute_name: str
        has to mach exactly one of the attributes of Simple_daily_stats,
        otherwise reises AttributeError
    """
    if attribute_name == "date":
        return daily_stat.date
    if attribute_name == "ips":
        return daily_stat.ips
    if attribute_name == "requests":
        return daily_stat.requests
    if attribute_name == "sessions":
        return daily_stat.sessions

    raise AttributeError(
        "Attribute", attribute_name, "does not exist for an object of type Daily_stats"
    )

def _attr_to_str(daily_stat: Simple_daily_stats, attribute_name: str) -> str:
    if attribute_name == "date":
        return daily_stat.date.isoformat()
    
    return str(simple_daily_stat_getattr(daily_stat, attribute_name))


def simple_daily_stats_from_log(
    log_entry: str, log_format: Optional[str] = None, delim: Optional[str] = None
) -> Simple_daily_stats:
    
    log_format = LOG_FORMAT if log_format is None else log_format
    delim = LOG_DELIM if delim is None else delim

    attr_val = dict(zip(log_format.split(), log_entry.split(delim)))

    return Simple_daily_stats(
        date=date_from_isoformat(attr_val["date"]),
        ips=int(attr_val["ips"]),
        requests=int(attr_val["requests"]),
        sessions=int(attr_val["sessions"]),
    )
