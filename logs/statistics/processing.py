import datetime
import json
import re
from typing import Callable, Dict, Optional, Set, TextIO, Tuple
from logs.helpers.simplelogger import SimpleLogger

from logs.parser.logparser import LogEntry, regex_parser
from logs.statistics.constants import (
    BOT_URL_REGEX,
    BOT_USER_AGENT_REGEX,
    LOG_DT_FORMAT,
    SESSION_DELIM,
)
from logs.statistics.dailystat import DailyStats
from logs.statistics.groupstats import GroupStats
from logs.statistics.ipstats import IpStats
from logs.statistics.logstats import LogStats

RE_PATTERN_BOT_USER_AGENT = re.compile(BOT_USER_AGENT_REGEX)
RE_PATTERN_BOT_URL = re.compile(BOT_URL_REGEX)

NO_URL = ""


def make_stats(
    input: TextIO,
    config_f: Optional[str],
    logger: Optional[SimpleLogger] = None,
    cached_log_stats: Optional[LogStats] = None,
) -> LogStats:
    """Parses and processes log in `input`
    and stores statistical information about the log in `log_stats`.

    Parameters
    ----------
    input: TextIO
        log files as plaintext
    log_stats: LogStats
    config_f: str, optional
        path to a blacklist file containing ip addressed considered as bots
    logger: SimpleLogger, optional
        default: `None`; if given then the duration of making stats will be logged
    cached_log_stats: LogStats, optional
        default: new empty `LogStats` object;
        log_stats object in which statiscics from `input` will be stored,
        containg laoded stats from chache.
        When parsing, not entries older then cached_log_stats.last_entry_ts will be added.

    Returns
    -------
    Log_stat
        containing information about log from `input`

    Note
    ----
    Log entries in input should be ordered by their time.
    New session is recognized when time of given entry is
    at least SESSION_DELIM seconds after the time of the
    last entry for the same host.

    """
    log_stats = LogStats() if cached_log_stats is None  else cached_log_stats
    from_time = log_stats.last_entry_ts

    if logger is not None:
        logger.addTask("Data parsing and proccessing")
    
    bots_set = set()
    if config_f is not None:
        with open(config_f, "r") as f:
            bots_set = set(ip_addr for ip_addr in f)

    for buffer in regex_parser(input):
        for entry in buffer:
            if len(entry) == 9:  # correct format of the log entry
                _log_stats_add_entry(log_stats, entry, bots_set, from_time)
            elif logger is not None:
                logger.logMessage(f"log entry parsing has failed (len={len(entry)}):\n{entry}")

    if logger is not None:
        logger.finishTask("Data parsing and proccessing")

    return log_stats


def _determine_bot(
    entry: LogEntry, *args: Callable[[LogEntry], bool]
) -> Tuple[bool, str]:
    """Classifies log entry as a bot if User-agent contains an URL
    or if a predicate from *args called on the entry is true

    Parameters
    ----------
    entry : LogEntry
        the log entry which will be classified

    *args: Callable[[LogEntry], bool])
        predicates on LogEntry which will

    Returns
    -------
    Tuple[bool, str]
        - (True, <url>) if the entry is classified as bot based on url in user_agent
        - (True, NO_URL) if the bot classified based on predicate in *args
        - (False, NO_URL)  otherwise
    """
    match = RE_PATTERN_BOT_URL.search(entry.user_agent)
    if match is not None:
        return (True, match.group(1))

    for func in args:
        if func(entry):
            return (True, NO_URL)

    return (False, NO_URL)


def determine_bot(
    entry: LogEntry, bots_set: Optional[Set[str]] = set()
) -> Tuple[bool, str]:
    """Classifies log entry as a bot if User-agent contains an URL
    or if User agent matches with `BOT_USER_AGENT_REGEX` or `entry.ip_addr`
    is in the `bots_set`

    Parameters
    ----------
    entry : LogEntry
        the log entry which will be classified

    bots_set: Set[str], optional
        default: empty set; set of IPs wich will be
        automaticaly classified as bots.

    Returns
    -------
    Tuple[bool, str]
        - (True, <url>) if the entry is classified as bot based on url in user_agent
        - (True, NO_URL) if the bot classified based on `bot_set` or `BOT_USER_AGENT_REGEX`
        - (False, NO_URL)  otherwise
    """
    return _determine_bot(
        entry,
        lambda x: x.ip_addr in bots_set,
        lambda x: RE_PATTERN_BOT_USER_AGENT.search(x.user_agent) is not None,
    )


def resolve_and_group_ips(
    log_stats: LogStats, ip_map: Dict[str, str] = {}, logger: Optional[SimpleLogger] = None,
) -> None:
    """Resolves ip address for all data in `log_stats.year_data`
    and merges same ips together.

    Note
    ----
    Somtimes IpStats.ip_addr is a host name, not IP address.
    This function basicly solves the problem for all
    stored data in `log_stats`

    Parameters
    ----------
    logs_stats: LogStats
    ip_map: Dict[str, str], optional
        maps invalid adress to resolved address
    logger: SimpleLogger, optional
        default: `None`; if given then the duration of this function will be logged
    """
    if logger is not None:
        logger.addTask("IPs resolving and merging")

    for bots, people in log_stats.year_stats.values():
        _resolve_and_group_ips_in_group_stats(bots, ip_map)
        _resolve_and_group_ips_in_group_stats(people, ip_map)
        # log_stats.year_stats[year] = (bots, people)

    # resolve and merge log_stats.daily_data
    # now all ips were already resoved and invalid are saved in ip_map
    for date, data in log_stats.daily_data.items():
        ips: Set[str] = data.ips
        grouped_ips: Set[str] = set()

        for ip in ips:
            resolved = ip_map.get(ip)
            grouped_ips.add(ip if resolved is None else resolved)
        log_stats.daily_data[date] = DailyStats(
            date, grouped_ips, data.requests, data.sessions
        )

    if logger is not None:
        logger.finishTask("IPs resolving and merging")


def _resolve_and_group_ips_in_group_stats(
    g_stats: GroupStats, ip_map: Optional[Dict[str, str]] = None
) -> None:
    """Resolves ip address in `g_stats`
    and merges data for same ips together.

    When IpStats are merged together, then
    the most frequent (based on session count) is selcted the

    Parameters
    ----------
    g_stats: GroupStats
        GroupStats which will be modified
    ip_map: Dict[str, str], optional
        maps invalid adress to resolved address
    """
    grouped_stats: Dict[str, IpStats] = {}
    hostname_aggregation_dict: Dict[str, Dict[str, int]] = {}
    # maps valid ips to a dict that maps hostnames of give in to session_count

    for stat in g_stats.stats.values():
        if stat.valid_ip is None:
            stat.ensure_valid_ip_address(ip_map)

        ip = stat.ip_addr
        grouped = grouped_stats.get(ip)

        if grouped is not None:
            stat.requests_num += grouped.requests_num
            stat.sessions_num += grouped.sessions_num

            # aggregate hostname
            hostnames = hostname_aggregation_dict.get(
                ip, {grouped.host_name: grouped.sessions_num}
            )
            hostnames[stat.host_name] = stat.sessions_num + hostnames.get(
                stat.host_name, 0
            )
            hostname_aggregation_dict[ip] = hostnames

        grouped_stats[ip] = stat

    # set as a hostname the most common
    for ip, hostnames in hostname_aggregation_dict.items():
        if len(hostnames) > 1:
            most_common_name, _ = sorted(
                hostnames.items(), key=lambda name_val_pair: name_val_pair[1])[-1]
            grouped_stats[ip].host_name = most_common_name

    g_stats.stats = grouped_stats


def group_bots_on_url(log_stats: LogStats, logger: Optional[SimpleLogger] = None) -> None:
    if logger is not None:
        logger.addTask("Grouping bots on User agent")

    for bots, _ in log_stats.year_stats.values():
        grouped_stats: Dict[str, IpStats] = {}
        ip_aggregation_dict: Dict[str, Dict[str, int]] = {}
        # maps urls to a dict that maps ips to requests_count

        for stat in bots.stats.values():
            if stat.bot_url == NO_URL:
                grouped_stats[stat.ip_addr] = stat
                continue

            grouped = grouped_stats.get(stat.bot_url)
            stat.requests_num += 0 if grouped is None else grouped.requests_num
            stat.sessions_num += 0 if grouped is None else grouped.sessions_num
            grouped_stats[stat.bot_url] = stat

            # aggregate ip
            if stat.bot_url not in ip_aggregation_dict:
                ip_aggregation_dict[stat.bot_url] = {}

            ips = ip_aggregation_dict.get(stat.bot_url)
            ips[stat.ip_addr] = stat.requests_num + ips.get(stat.ip_addr, 0)

        # set as a IP the most common
        for url, ips in ip_aggregation_dict.items():
            if len(ips) > 1:
                most_common_ip, _ = sorted(
                    ips.items(), key=lambda ip_request_pair: ip_request_pair[1])[-1]
                grouped_stats[url].ip = most_common_ip

        bots.stats = grouped_stats
            
    if logger is not None:
        logger.finishTask("Grouping bots on User agent")





def _log_stats_add_entry(
    log_stats: LogStats,
    entry: LogEntry,
    bots_set: Optional[Set[str]],
    from_time: datetime.datetime,
):
    """Adds one `entry` to the statistical informations stored in `log_stats`

    Parameters
    ----------
    log_stats: LogStats
    entry: LogEntry
    bots_set: Optional[Set[str]]
        set of IPv4 from blacklist - all entries from these
        ips will be classified as bots
    from_time: datetime.datetime
        only entries with time attribute later than `from_time` will be added
    """
    dt = datetime.datetime.strptime(entry.time, LOG_DT_FORMAT)
    if dt <= from_time:
        # skip entry earlier than `from_time`
        return

    if dt > log_stats.last_entry_ts:
        log_stats.last_entry_ts = dt

    if log_stats.current_year != dt.year:
        log_stats.switch_year(dt.year)

    is_bot, bot_url = determine_bot(entry, bots_set)
    group_stats = log_stats.bots if is_bot else log_stats.people
    ip_stat = group_stats.stats.get(entry.ip_addr, IpStats(entry.ip_addr, is_bot, bot_url))

    new_sess = _ip_stats_add_entry(ip_stat, entry)
    # 1 if new session was created, 0 otherwise

    group_stats.stats[entry.ip_addr] = ip_stat
    group_stats.day_req_distrib[ip_stat.datetime.hour] += 1
    group_stats.week_req_distrib[ip_stat.datetime.weekday()] += 1
    group_stats.month_req_distrib[ip_stat.datetime.month - 1] += 1
    group_stats.day_sess_distrib[ip_stat.datetime.hour] += new_sess
    group_stats.week_sess_distrib[ip_stat.datetime.weekday()] += new_sess
    group_stats.month_sess_distrib[ip_stat.datetime.month - 1] += new_sess

    # making daily_data for picture overview
    date = ip_stat.datetime.date()
    _, ip_addrs, req_num, sess_num = log_stats.daily_data.get(
        date, DailyStats(date, set(), 0, 0)
    )
    ip_addrs.add(ip_stat.ip_addr)
    if not ip_stat.is_bot and new_sess:
        sess_num += 1
    log_stats.daily_data[date] = DailyStats(date, ip_addrs, req_num + 1, sess_num)


def _ip_stats_add_entry(ip_stat: IpStats, entry: LogEntry) -> int:
    """ "Adds `entry` to the `ip_stats`.
    If  new session is recognized returns `1`, else `0`.
    `entry` is considered in new session if the duration from
    `ip_stat.datetime` to `entry.time` is at least `SESSION_DELIM`.
    Beacuse there is no way how to enter older sessions,
    the entries has to be added in in their time order,
    otherwiese the return value is meaningless."""
    rv = 0
    dt = datetime.datetime.strptime(entry.time, LOG_DT_FORMAT)

    if abs(dt - ip_stat.datetime) >= datetime.timedelta(minutes=SESSION_DELIM):
        ip_stat.sessions_num += 1
        rv = 1

    ip_stat.requests_num += 1
    ip_stat.datetime = dt
    return rv


def save_log_stats(log_stat: LogStats, f_name: str, logger: Optional[SimpleLogger] = None):
    """Transforms `log_stat` into json and saves it to a file with path `f_name`.
    If `logger` is given then the duration of this function will be logged
    """
    if logger is not None:
        logger.addTask("Saving log stats")

    with open(f_name, "w") as f:
        json.dump(log_stat.json(), f)

    if logger is not None:
        logger.finishTask("Saving log stats")


def load_log_stats(f_name: str, logger: Optional[SimpleLogger] = None) -> LogStats:
    """Load statistical informations from json file with path `f_name`
    to new Log_stat.
    If `logger` is given then the duration of this function will be logged

    Returns
    -------
    LogStats
        containing loaded json
    """
    if logger is not None:
        logger.addTask("Loading stats")

    log_stats = LogStats()
    with open(f_name, "r") as f:
        log_stats.from_json(json.load(f))

    if logger is not None:
        logger.finishTask("Saving log stats")

    return log_stats
