import datetime
import json
import sys
import re
from typing import Callable, Dict, Optional, Set, TextIO, Tuple

from logs.statistics.constants import LOG_DT_FORMAT
from logs.statistics.helpers import Ez_timer
from logs.parser.log_parser import Log_entry, regex_parser
from logs.statistics.constants import (
    BOT_URL_REGEX,
    BOT_USER_AGENT_REGEX,
    SESSION_DELIM,
)
from logs.statistics.dailystat import Daily_stats
from logs.statistics.groupstats import Group_stats
from logs.statistics.ipsatats import Ip_stats
from logs.statistics.logstats import Log_stats


RE_PATTERN_BOT_USER_AGENT = re.compile(BOT_USER_AGENT_REGEX)
RE_PATTERN_BOT_URL = re.compile(BOT_URL_REGEX)


def make_stats(
    input: TextIO, config_f: Optional[str], err_msg: bool = False
) -> Log_stats:
    """Parses and processes log in `input`
    and stores statistical information about the log in `log_stats`.

    Parameters
    ----------
    input: TextIO
        log files as plaintext
    log_stats: Log_stats
    config_f: str, optional
        path to a blacklist file containing ip addressed considered as bots
    err_msg: bool, optional
        default: `False`; if `True` then the duration of making stats will be
        printed to std.err

    Returns
    -------
    Log_stat
        containing information about log from `input`

    Note
    ----
    Log entries in input has to be ordered by their time.
    New session is recognized when time of given entry is
    at least SESSION_DELIM seconds after the time of the
    last entry for the same host.

    """
    if err_msg:
        timer = Ez_timer("Data parsing and proccessing")

    log_stats = Log_stats()

    bots_set = set()
    if config_f is not None:
        with open(config_f, "r") as f:
            bots_set = set(ip_addr for ip_addr in f)

    for buffer in regex_parser(input):
        for entry in buffer:
            if len(entry) == 9:  # correct format of the log entry
                _log_stats_add_entry(log_stats, entry, bots_set)
            elif err_msg:
                print(
                    f"log entry parsing failed (len={len(entry)}):\n",
                    entry,
                    file=sys.stderr,
                )

    if err_msg:
        timer.finish()

    return log_stats


def _determine_bot(
    entry: Log_entry, *args: Callable[[Log_entry], bool]
) -> Tuple[bool, str]:
    """Classifies log entry as a bot if User-agent contains an URL
    or if a predicate from *args called on the entry is true

    Parameters
    ----------
    entry : Log_entry
        the log entry which will be classified

    *args: Callable[[Log_entry], bool])
        predicates on Log_entry which will

    Returns
    -------
    Tuple[bool, str]
        - (True, <url>) if the entry is classified as bot based on url in user_agent
        - (True, "") if the bot classified based on predicate in *args
        - (False, "")  otherwise
    """
    match = RE_PATTERN_BOT_URL.search(entry.user_agent)
    if match is not None:
        return (True, match.group(1))

    for func in args:
        if func(entry):
            return (True, "")

    return (False, "")


def determine_bot(
    entry: Log_entry, bots_set: Optional[Set[str]] = set()
) -> Tuple[bool, str]:
    return _determine_bot(
        entry,
        lambda x: x.ip_addr in bots_set,
        lambda x: RE_PATTERN_BOT_USER_AGENT.search(x.user_agent) is not None,
    )


def resolve_and_group_ips(
    log_stats: Log_stats, ip_map: Dict[str, str] = {}, err_msg: bool = False
) -> None:
    """Resolves ip address for all data in `log_stats.year_data`
    and merges same ips together.

    Note
    ----
    Somtimes Ip_stats.ip_addr is a host name, not IP address.
    This function basicly solves the problem for all
    stored data in `log_stats`

    Parameters
    ----------
    logs_stats: Log_stats
    ip_map: Dict[str, str], optional
        maps invalid adress to resolved address
    err_msg: bool, optional
        default: `False`; if `True` then the duration of this function will be
        printed to std.err
    """
    if err_msg:
        timer = Ez_timer("IPs resolving and merging")

    for vals in log_stats.year_stats.values():
        bots, people = vals[0], vals[1]

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
        log_stats.daily_data[date] = Daily_stats(
            date, grouped_ips, data.requests, data.sessions
        )

    if err_msg:
        timer.finish()


def _resolve_and_group_ips_in_group_stats(
    g_stats: Group_stats, ip_map: Optional[Dict[str, str]] = None
) -> None:
    """Resolves ip address in `g_stats`
    and merges data for same ips together

    Parameters
    ----------
    g_stats: Group_stats
        Group_stats which will be modified
    ip_map: Dict[str, str], optional
        maps invalid adress to resolved address
    """
    grouped_stats: Dict[str, Ip_stats] = {}

    for stat in g_stats.stats.values():
        stat.ensure_valid_ip_address(ip_map)
        ip = stat.ip_addr

        grouped = grouped_stats.get(ip)
        stat.requests_num += 0 if grouped is None else grouped.requests_num
        stat.sessions_num += 0 if grouped is None else grouped.sessions_num
        grouped_stats[ip] = stat

    g_stats.stats = grouped_stats




def _log_stats_add_entry(
    log_stats: Log_stats, entry: Log_entry, bots_set: Optional[Set[str]]
):
    """Adds one `entry` to the statistical informations stored in `log_stats`

    Parameters
    ----------
    log_stats: Log_stats
    entry: Log_entry
    bots_set: Optional[Set[str]]
        set of IPv4 from blacklist - all entries from these
        ips will be classified as bots
    """
    dt = datetime.datetime.strptime(entry.time, LOG_DT_FORMAT)
    if log_stats.current_year != dt.year:
        log_stats.switch_year(dt.year)

    is_bot, bot_url = determine_bot(entry, bots_set)
    group_stats = log_stats.bots if is_bot else log_stats.people
    ip_stat = group_stats.stats.get(entry.ip_addr, Ip_stats(entry, is_bot, bot_url))

    new_sess = _ip_stats_add_entry(ip_stat, entry)
    # 1 if new session was created, 0 otherwise

    group_stats.stats[entry.ip_addr] = ip_stat
    group_stats.day_req_distrib[ip_stat.datetime.hour] += 1
    group_stats.week_req_distrib[ip_stat.datetime.weekday()] += 1
    group_stats.month_req_distrib[(ip_stat.datetime.year, ip_stat.datetime.month)] += 1
    group_stats.day_sess_distrib[ip_stat.datetime.hour] += new_sess
    group_stats.week_sess_distrib[ip_stat.datetime.weekday()] += new_sess
    group_stats.month_sess_distrib[
        (ip_stat.datetime.year, ip_stat.datetime.month)
    ] += new_sess

    # making daily_data for picture overview
    date = ip_stat.datetime.date()
    _, ip_addrs, req_num, sess_num = \
        log_stats.daily_data.get(date, Daily_stats(date, set(), 0, 0))
    ip_addrs.add(ip_stat.ip_addr)
    if not ip_stat.is_bot and new_sess:
        sess_num += 1
    log_stats.daily_data[date] = Daily_stats(date, ip_addrs, req_num + 1, sess_num)


def _ip_stats_add_entry(ip_stat: Ip_stats, entry: Log_entry) -> int:
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


def save_log_stats(log_stat: Log_stats, f_name: str, err_msg: bool = False):
    """Transforms `log_stat` into json and saves it to a file with path `f_name`.
    If `err_msg` is `True`, then prints duration if saving to std.err
    """
    if err_msg:
        time1 = Ez_timer("Saving log stats")

    with open(f_name, "w") as f:
        json.dump(log_stat.json(), f)

    if err_msg:
        time1.finish()


def load_log_stats(f_name: str, err_msg: bool = False) -> Log_stats:
    """Load statistical informations from json file with path `f_name`
    to new Log_stat.
    If `err_msg` is `True`, then prints duration if loading to std.err

    Returns
    -------
    Log_stats
        containing loaded json
    """
    if err_msg:
        time1 = Ez_timer("Loading stats")

    log_stats = Log_stats()
    with open(f_name, "r") as f:
        log_stats.from_json(json.load(f))

    if err_msg:
        time1.finish()

    return log_stats
