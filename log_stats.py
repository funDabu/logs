from collections import Counter
import sys, os
import socket
import datetime
import matplotlib.pyplot as plt
import io
import random
import requests
import time
import json, re
from log_parser import Log_entry, parse_entry_with_regex, regex_parser
from html_maker import Html_maker, make_table
from typing import List, TextIO, Optional, Tuple, Dict, Set, Callable
from geoloc_db import GeolocDB


"""
========== CONSTANTS ==========
"""
from constants import LOG_DT_FORMAT, DT_FORMAT, DATE_FORMAT, MONTHS, DAYS

BOT_URL_REGEX = r"(http\S+?)[);]"
RE_PATTERN_BOT_URL = re.compile(BOT_URL_REGEX)

SIMPLE_IPV4_REGEX = r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}"
RE_PATTERN_SIMPLE_IPV4 = re.compile(SIMPLE_IPV4_REGEX)

SESSION_DELIM = 1  # in minutes


"""
========== EASY TIMER ==========
"""


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


"""
========== FUNCTIONS ==========
"""

def strp_date(date: str, format: str) -> datetime.date:
    dt = datetime.datetime.strptime(date, format)
    return dt.date()


def get_bot_url(user_agent: str) -> str:
    # if "user agent" field of the log entry doesn't contain
    #   bot's url, returns empty string
    match = RE_PATTERN_BOT_URL.search(user_agent)
    if match is None:
        return ""
    return match.group(1)


def determine_bot(entry:Log_entry, *args: Callable[[Log_entry], bool]) -> Tuple[bool, str]:
    """ Classifies log entry as a bot if User-agent contains an URL
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


def anotate_bars(xs: List[float], ys: List[float], labels: List[int], rotation: int):
    for i, x in enumerate(xs):
        plt.annotate(str(labels[i]), (x, ys[i]),
                     rotation=rotation, horizontalalignment='center')

"""
========== CLASSES ==========
"""

class Ip_stats:
    """Data structure to store informations about requests
    from a single IP address

    Attributes
    ----------
    ip_addr: str
    host_name: str
    geolocation: str
    bot_url: str
    is_bot: bool
    requests_num: int
    sessions_num: int
    datetime: datetime
    """
    geoloc_tokens = None # www.geoplugin.net api oficial limit is 120 requsts/min
    last_geoloc_ts = time.time() # time stamp of last call to geolocation API
    session = requests.Session() # to call geolocation API
    database = None # database of saved geolocations

    __slots__ = ("ip_addr", "host_name", "geolocation", "bot_url",
                 "is_bot", "requests_num", "sessions_num", "datetime")

    def __init__(self,
                 entry:Log_entry,
                 is_bot:Optional[bool]=None,
                 bot_url="",
                 json:Optional[str]=None)\
        -> None:

        if json is not None:
            self._from_json(json)
            return

        self.ip_addr = entry.ip_addr
        self.host_name = "Unresolved"
        self.geolocation = ""
        self.requests_num = 0
        self.sessions_num = 0
        self.datetime = datetime.datetime.strptime("01/Jan/1980:00:00:00 +0000",
                                                   LOG_DT_FORMAT)

        if is_bot is None:
            self.is_bot, self.bot_url = determine_bot(entry)
            return

        self.is_bot, self.bot_url = is_bot, bot_url

    def update_host_name(self) -> None:
        try:
            self.host_name = socket.gethostbyaddr(self.ip_addr)[0]
        except:
            self.host_name = "Unknown"
    
    def get_short_host_name(self, precision: int = 3) -> str:
        hostname = self.host_name
        hostname = hostname.rsplit('.')

        if len(hostname) > precision:
            hostname = hostname[-precision:]

        hostname = '.'.join(hostname)
        return hostname
    
    def ensure_valid_ip_address(self) -> bool:
        """Does a simple incomplete validation of `self.ip_addr`.
        If `self.ip_addr` in not an IP address,
        than it might be a domain name, 
        so a DNS lookup will be made to find corresponding IP address
        and `self.ip_addr` will be set accordingly.

        Returns
        -------
        True
            If `self.ip_addr` probably contains valid ip address
        
        False
            If `self.ip_addr` is not valid and the address could not be resolved
        """
        match = RE_PATTERN_SIMPLE_IPV4.search(self.ip_addr)
        if match is not None:
            return True
        
        try:
            addr = socket.gethostbyname(self.ip_addr)
            self.host_name = self.ip_addr
            self.ip_addr = addr
            return True
        except:
            return False


    def add_entry(self, entry: Log_entry) -> int:
        # Returns 1 if <entry> is a new session, 0 otherwise
        rv = 0
        dt = datetime.datetime.strptime(entry.time, LOG_DT_FORMAT)


        if abs(dt - self.datetime) >= datetime.timedelta(minutes=SESSION_DELIM):
            self.sessions_num += 1
            rv = 1

        self.requests_num += 1
        self.datetime = dt
        return rv

    def update_geolocation(self):
        if Ip_stats.database is None:
            self.geolocate_with_api()
            return

        val = Ip_stats.database.get_geolocation(self.ip_addr)
        if val is not None:
            self.geolocation, _ = val
            return

        self.geolocate_with_api()
        Ip_stats.database.insert_geolocation(self.ip_addr, self.geolocation)
    
    def geolocate_with_api(self):
        if not self.ensure_valid_ip_address():
            self.geolocation = "Unknown"
            return

        token_max = 3
        sleep_time = 2 # seconds

        if Ip_stats.geoloc_tokens is None\
           or Ip_stats.last_geoloc_ts - time.time() > sleep_time:

            Ip_stats.geoloc_tokens = token_max
        
        if not Ip_stats.geoloc_tokens:
            time.sleep(sleep_time)
            Ip_stats.geoloc_tokens = token_max

        Ip_stats.geoloc_tokens -= 1
        Ip_stats.last_geoloc_ts = time.time()
        self._geoplugin_call()

    def _geoplugin_call(self):
        try:
            country = Ip_stats.session.get(
                f"http://www.geoplugin.net/json.gp?ip={self.ip_addr}").json()
            self.geolocation = country['geoplugin_countryName']
        except:
            self.geolocation = "Unknown"
    
    def _get_attr(self, name:str):
        if name == "datetime":
            return self.datetime.__format__(DT_FORMAT)
        return getattr(self, name, None)

    def json(self):
        return {key : self._get_attr(key) for key in self.__slots__}

    def _set_attr(self, name, data):
        if name == "datetime":
            self.datetime = datetime.datetime.strptime(data, DT_FORMAT)
        else:
            setattr(self, name, data)

    def _from_json(self, js):
        for slot in self.__slots__:
            self._set_attr(slot, js[slot])


class Stat_struct:
    __slots__ = ("stats",
                 "day_req_distrib", "week_req_distrib", "month_req_distrib",
                 "day_sess_distrib", "week_sess_distrib", "month_sess_distrib",)

    def __init__(self, js:Optional[Dict]=None):
        if js is not None:
            self.from_json(js)
            return 

        self.stats: Dict[str, Ip_stats] = {}
        self.day_req_distrib = [0 for _ in range(24)]
        self.day_sess_distrib = [0 for _ in range(24)]
        self.week_req_distrib = [0 for _ in range(7)]
        self.week_sess_distrib = [0 for _ in range(7)]
        self.month_req_distrib = Counter()
        self.month_sess_distrib = Counter()

    def _get_attr(self, name:str):
        if name == "stats":
            return {key : stat.json() for key, stat in self.stats.items()}
        if name == "month_req_distrib":
            to_str = lambda x: f"{x[0]},{x[1]}"
            return {to_str(key) : val for key, val in self.month_req_distrib.items()}
        if name == "month_sess_distrib":
            to_str = lambda x: f"{x[0]},{x[1]}"
            return {to_str(key) : val for key, val in self.month_sess_distrib.items()}
        
        return getattr(self, name, None)
    
    def _set_attr(self, name, data):
        if name == "stats":
            self.stats = {key : Ip_stats(None, json=stat) for key, stat in data.items()}
        elif name == "month_req_distrib":
            to_tuple = lambda x: tuple(map(int, x.split(",")))
            self.month_req_distrib = Counter({to_tuple(key) : val
                                              for key, val in data.items()})
        elif name == "month_sess_distrib":
            to_tuple = lambda x: tuple(map(int, x.split(",")))
            self.month_sess_distrib = Counter({to_tuple(key) : val
                                               for key, val in data.items()})
        else:
            setattr(self, name, data)

    def json(self):
        return {slot : self._get_attr(slot) for slot in self.__slots__}
    
    def from_json(self, js):
        for slot in self.__slots__:
            self._set_attr(slot, js[slot])


class Log_stats:
    def __init__(self, input: Optional[TextIO] = None, err_msg=False, config_f=None):
        self.bots = Stat_struct() # for curretnt year
        self.people = Stat_struct() # for curretnt year
        self.err_msg = err_msg

        self.daily_data: Dict[datetime.date, Tuple[Set[str], int, int]] = {}
        # ^: date -> (unique_ips, requests_number, people_session_number)
        # ^: for picture overview

        self.year_stats: Dict[int, Tuple(Stat_struct, Stat_struct)] = {}
        # ^: year -> (bots, people); contains all Stat_structs

        self.current_year = None

        if config_f is not None:
            # concfig file contains IP adresses considered as bots
            self.initialize_bot_set(config_f)
        else:
            self.bots_set = set()

        if input:
            self.make_stats(input)

    def _get_attr(self, name:str):
        if name == "bots":
            return self.bots.json()
        if name == "people":
            return self.people.json()

        if name == "daily_data":
            return {d.__format__(DATE_FORMAT): (list(ips), r, s)
                        for d, (ips, r, s) in self.daily_data.items()}
        
        if name == "year_stats":
            return {y : (b.json(), p.json()) for y, (b, p) in self.year_stats.items()}
        
        if name == "bots_set":
            return list(self.bots_set)
        
        return getattr(self, name, None)
    
    def _set_attr(self, name, data):
        if name == "bots":
            self.bots = Stat_struct(data)
        elif name == "people":
            self.people = Stat_struct(data)
        elif name == "daily_data":
            self.daily_data = {strp_date(d, DATE_FORMAT): (set(ips), r, s)
                                    for d, (ips, r, s) in data.items()}
        elif name == "year_stats":
            self.year_stats = {int(year): (Stat_struct(b), Stat_struct(p))
                                    for year, (b, p) in data.items()}
        elif name == "bots_set":
            self.bots_set = set(data)
        else:
            setattr(self, name, data)
    
    def json(self):
        return {key: self._get_attr(key) for key in self.__dict__.keys()}
    
    def from_json(self, js):
        for key, data in js.items():
            self._set_attr(key, data)

    def save(self, f_name: str):
        if self.err_msg:
            time1 = Ez_timer("Saving stats")

        with open(f_name, "w") as f:
            json.dump(self.json(), f)
        
        if self.err_msg:
            time1.finish()

    # DEBUG
    # def save(self, f_name: str):
    #     if self.err_msg:
    #         time1 = Ez_timer("Saving stats")

    #     output = self.json()

    #     print(output)
    #     print()
    #     print(str(output))

    #     with open(f_name, "w") as f:
    #         json.dump(output, f)
        
    #     if self.err_msg:
    #         time1.finish()

    def load(self, f_name: str):
        if self.err_msg:
            time1 = Ez_timer("Loading stats")

        with open(f_name, "r") as f:
            self.from_json(json.load(f))

        if self.err_msg:
            time1.finish()
    
    def initialize_bot_set(self, config_file_path: str) -> None:
        with open(config_file_path, "r") as f:
            self.bots_set = set(ip_addr for ip_addr in f)

    def make_stats_with_buffer_parser(self, input: TextIO):
        if self.err_msg:
            timer = Ez_timer("Data parsing and proccessing")

        for buffer in regex_parser(input):
            for entry in buffer:
                if len(entry) == 9:  # correct format of the log entry
                    self._add_entry(entry)
                elif self.err_msg:
                    print(f"log entry parsing failed (len={len(entry)}):\n",
                          entry, file=sys.stderr)

        if self.err_msg:
            timer.finish()
        
        # save current year in case it's not already saved
        self._switch_years(self.current_year)

    def make_stats_without_buffer(self, input: TextIO):
        # not currently used, not clear if is really slower than make_stats_with_buffer
        if self.err_msg:
            timer = Ez_timer("Data parsing and proccessing")

        for line in input:
            # entry = parse_log_entry(line)
            entry = parse_entry_with_regex(line)

            if len(entry) == 9:  # correct format of the log entry
                self._add_entry(entry)
            elif self.err_msg:
                print("log entry parsing failed:\n\t", entry, file=sys.stderr)

        if self.err_msg:
            timer.finish()
        
        # save current year in case it's not already saved
        self._switch_years(self.current_year)
    
    def make_stats(self, input: TextIO):
        # self.make_stats_without_buffer(input)
        self.make_stats_with_buffer_parser(input)

    def _add_entry(self, entry: Log_entry):
        dt = datetime.datetime.strptime(entry.time, LOG_DT_FORMAT)
        if self.current_year != dt.year:
            self._switch_years(dt.year)

        is_bot, bot_url = determine_bot(entry, lambda x: x.ip_addr in self.bots_set)

        entry_key = bot_url if is_bot and len(bot_url) > 0\
                    else entry.ip_addr
        stat_struct = self.bots if is_bot else self.people

        ip_stat = stat_struct.stats.get(entry_key)
        if ip_stat is None:
            ip_stat = Ip_stats(entry, is_bot, bot_url)
            
        new_sess = ip_stat.add_entry(entry)
        # ^: 1 if new session was created, 0 otherwise

        stat_struct.stats[entry_key] = ip_stat
        stat_struct.day_req_distrib[ip_stat.datetime.hour] += 1
        stat_struct.week_req_distrib[ip_stat.datetime.weekday()] += 1
        stat_struct.month_req_distrib[(ip_stat.datetime.year, ip_stat.datetime.month)] += 1
        stat_struct.day_sess_distrib[ip_stat.datetime.hour] += new_sess
        stat_struct.week_sess_distrib[ip_stat.datetime.weekday()] += new_sess
        stat_struct.month_sess_distrib[(
            ip_stat.datetime.year, ip_stat.datetime.month)] += new_sess

        # making daily_data for picture overview
        date = ip_stat.datetime.date()
        ip_addrs, req_num, sess_num = self.daily_data.get(date, (set(), 0, 0))
        ip_addrs.add(ip_stat.ip_addr)
        if not ip_stat.is_bot and new_sess:
            sess_num += 1
        self.daily_data[date] = (ip_addrs, req_num + 1, sess_num)

    def _switch_years(self, year: int):
        if self.current_year is not None:
            self.year_stats[self.current_year] = (self.bots, self.people)

        self.current_year = year
        self.bots, self.people =\
            self.year_stats.get(year, (Stat_struct(), Stat_struct()))

    def print_stats(self,
                    output: TextIO,
                    geoloc_sample_size,
                    selected=True,
                    year=None,
                    geoloc_db:Optional[str]= None):
        html: Html_maker = Html_maker()
        
        if year is not None:
            self._switch_years(year)
            html.append(f"<h1>Year {self.current_year}</h1>")
        
        if geoloc_db is not None:
            Ip_stats.database = GeolocDB(geoloc_db)

        if self.err_msg:
            timer = Ez_timer("making charts of bots and human users")

        self._print_bots(html, selected)
        self._print_users(html, selected)
        if self.err_msg:
            timer.finish()

        self._print_countries_stats(
            html, geoloc_sample_size, selected)

        print(html.html(), file=output)

    def test_geolocation(self,
                         output: TextIO,
                         geoloc_sample_size=300,
                         selected=True,
                         repetitions: int = 1,
                         year: int = None):
        if year is not None:
            self._switch_years(year)

        html: Html_maker = Html_maker()
        self._test_geolocation(html,
                               geoloc_sample_size,
                               selected=selected,
                               repetitions=repetitions)

        print(html.html(), file=output)

    def _print_bots(self,
                    html: Html_maker,
                    selected=True
                    ) -> None:
        html.append("<h2>Bots</h2>")

        req_sorted_stats, sess_sorted_stats = self._sort_stats(True)

        self._print_overview(html, "Bots count", req_sorted_stats)
        if len(req_sorted_stats) == 0:
            return

        selected = "selected" if selected else ""

        self._print_most_frequent(html,
                                  req_sorted_stats,
                                  sess_sorted_stats,
                                  True,
                                  selected)

        self._print_day_distribution(html, True, selected)
        self._print_week_distribution(html, True, selected)
        self._print_month_distributions(html, True, selected)

    def _print_users(self, html: Html_maker, selected=True):
        html.append("<h2>Human users</h2>")
        req_sorted_stats, sess_sorted_stats = self._sort_stats(False)

        self._print_overview(html,
                             "Different IP addresses count",
                             req_sorted_stats)
        if len(req_sorted_stats) == 0:
            return

        selected = "selected" if selected else ""

        self._print_most_frequent(html,
                                  req_sorted_stats,
                                  sess_sorted_stats,
                                  False,
                                  selected)
        self._print_day_distribution(html, False, selected)
        self._print_week_distribution(html, False, selected)
        self._print_month_distributions(html, False, selected)

    def _print_overview(self,
                        html: Html_maker,
                        header_str: str,
                        req_sorted_stats: List[Ip_stats]) -> None:
        total_session_num = sum(map(lambda ip_stat: ip_stat.sessions_num, req_sorted_stats))
        html.append(make_table("Overview",
                               [header_str, "Total sessions count"],
                               [[str(len(req_sorted_stats)), str(total_session_num)]],
                               ))

    def _sort_stats(self,
                    bot: bool
                    ) -> Tuple[List[Ip_stats], List[Ip_stats]]:
        if bot:
            stats = self.bots.stats
        else:
            stats = self.people.stats

        req_sorted_stats = sorted(stats.values(),
                                  key=lambda x: x.requests_num,
                                  reverse=True)
        sess_sorted_stats = sorted(stats.values(),
                                   key=lambda x: x.sessions_num,
                                   reverse=True)
        return (req_sorted_stats, sess_sorted_stats)


    def _ip_stats_iter(self, data: List[Ip_stats], n: int, bots: bool,  host_name=True):
        n = min(n, len(data))

        for i in range(n):
            ip_stat = data[i]
            if host_name and ip_stat.host_name == 'Unresolved':
                ip_stat.update_host_name()
            if not ip_stat.geolocation:
                ip_stat.update_geolocation()
                
            # yield a row
            yield [f"{i + 1}",
                   ip_stat.bot_url if bots else ip_stat.ip_addr,
                   ip_stat.get_short_host_name(),
                   ip_stat.geolocation,
                   ip_stat.requests_num,
                   ip_stat.sessions_num
                  ]
    
    def _attribs_for_most_freq_table_iter(self, data: List[Ip_stats], n: int):
        n = min(n, len(data))

        for i in range(n):
            yield ["", "", f"title='{data[i].host_name}'", "", "", ""]

    
    def _print_most_frequent(self,
                             html: Html_maker,
                             req_sorted_stats: List[Ip_stats],
                             sess_sorted_stats: List[Ip_stats],
                             bots: bool,
                             selected="",
                             host_name=True):

        html.append('<h3>Most frequent</h3>\n')
        uniq_classes = html.print_selection(["session table", "requests table"],
                                              [[selected]] * 2)
        html.append("<div class='flex-align-start'>")

        if bots:
            group_name = "bots"
            header = ["Rank", "Bot's url", "Host name",
                      "Geolocation", "Requests count", "Sessions count"]
        else:
            group_name = "human users"
            header = ["Rank", "IP address", "Host name",
                      "Geolocation", "Requests count", "Sessions count"]

        html.append(make_table(f"Most frequent {group_name} by number of sessions",
                               header,
                               self._ip_stats_iter(sess_sorted_stats, 20, host_name=host_name, bots=bots),
                               None,
                               ["selectable", selected, uniq_classes[0]],
                               self._attribs_for_most_freq_table_iter(sess_sorted_stats, 20)
                              ))

        html.append(make_table(f"Most frequent {group_name} by number of requests",
                               header,
                               self._ip_stats_iter(req_sorted_stats, 20, host_name=host_name, bots=bots),
                               None,
                               ["selectable", selected, uniq_classes[1]],
                               self._attribs_for_most_freq_table_iter(req_sorted_stats, 20)
                              ))

        html.append("</div>")

    def _print_day_distribution(self, html: Html_maker, bots, selected=""):
        group_name = "bots" if bots else "users"
        data = self.bots if bots else self.people

        def content_iter(data: Stat_struct):
            i = 0
            while i <= 24:
                if i < 24:
                    yield [f"{i}:00 - {i}:59",
                           str(data.day_req_distrib[i]),
                           str(data.day_sess_distrib[i])]
                else:
                    yield ["Sum",
                           str(sum(data.day_req_distrib)),
                           str(sum(data.day_sess_distrib))]
                i += 1

        html.append(
            "<h3>Distribution of across hours of day</h3>")
        uniq_classes = html.print_selection(
            ["table", "session graph", "request graph"],
            [[selected]] * 3)

        html.append("<div class='flex-align-start'>")
        html.append(make_table(
            f"Distribution of {group_name} across hours of day",
            ["Time", "Request count", "Sessions count"],
            content_iter(data),
            None,
            ["selectable", selected, uniq_classes[0]]))

        html.append(f'<div class="selectable {selected} {uniq_classes[1]}">')
        self._print_distribution_graph(html,
                                       data.day_sess_distrib,
                                       "hours",
                                       "session count",
                                       [f"{i}:00 - {i}:59" for i in range(24)],
                                       group_name,
                                       left_margin=True)
        html.append(
            f'</div>\n<div class="selectable {selected} {uniq_classes[2]}">')
        self._print_distribution_graph(html,
                                       data.day_req_distrib,
                                       "hours",
                                       "request count",
                                       [f"{i}:00 - {i}:59" for i in range(24)],
                                       group_name,
                                       left_margin=True)
        html.append("</div></div>")

    def _print_week_distribution(self, html: Html_maker, bots, selected=True):
        group_name = "bots" if bots else "users"
        data = self.bots if bots else self.people

        def contet_iter(data: Stat_struct):
            i = 0
            while i <= 7:
                if i < 7:
                    yield [DAYS[i],
                           str(data.week_req_distrib[i]),
                           str(data.week_sess_distrib[i])]
                else:
                    yield ["Sum",
                           str(sum(data.week_req_distrib)),
                           str(sum(data.week_sess_distrib))]
                i += 1

        html.append(
            "<h3>Distributions across week days</h3>")
        uniq_classes = html.print_selection(
            ["table", "session graph", "request graph"],
            [[selected]]*3)

        html.append("<div class='flex-align-start'>")
        html.append(make_table(f"Distributions of {group_name} across week days",
                               ["Day", "Request count", "Sessions count"],
                               contet_iter(data),
                               None,
                               ["selectable", selected, uniq_classes[0]]))

        html.append(f'<div class="selectable {selected} {uniq_classes[1]}">')
        self._print_distribution_graph(html,
                                       data.week_sess_distrib,
                                       "days of week",
                                       "session count",
                                       DAYS,
                                       group_name)
        html.append(
            f'</div>\n<div class="selectable {selected} {uniq_classes[2]}">')
        self._print_distribution_graph(html,
                                       data.week_req_distrib,
                                       "days of week",
                                       "request count",
                                       DAYS,
                                       group_name)
        html.append('</div></div>')

    def _print_month_distributions(self,
                                   html: Html_maker,
                                   bots: bool,
                                   selected: str = ""):
        group_name = "bots" if bots else "users"

        data = self.bots if bots else self.people
        session_distrib = sorted(
            data.month_sess_distrib.items(), key=lambda x: x[0])
        request_distrib = sorted(
            data.month_req_distrib.items(), key=lambda x: x[0])

        html.append(
            "<h3>Distributions accross months</h3>")
        uniq_classes = html.print_selection(
            ["sessions graph", "requests graph"],
            [[selected]]*2)

        html.append(
            f'<div class="flex-align-start">\n<div class="selectable {selected} {uniq_classes[0]}">')
        distrib_values = list(map(lambda x: x[1], session_distrib))
        distrib_keys = list(map(lambda x: x[0], session_distrib))
        self._print_distribution_graph(html,
                                       distrib_values,
                                       "months",
                                       "session count",
                                       [f'{MONTHS[k[1]]} {k[0]}' for k in distrib_keys],
                                       group_name,
                                       left_margin=True)

        html.append(
            f'</div>\n<div class="selectable {selected} {uniq_classes[1]}">')
        distrib_values = list(map(lambda x: x[1], request_distrib))
        distrib_keys = list(map(lambda x: x[0], request_distrib))
        self._print_distribution_graph(html,
                                       distrib_values,
                                       "months",
                                       "request count",
                                       [f'{MONTHS[k[1]]} {k[0]}' for k in distrib_keys],
                                       group_name,
                                       left_margin=True)
        html.append('</div>\n</div>')

    def _print_distribution_graph(self,
                                  html: Html_maker,
                                  data: List[float],
                                  xlabel: str,
                                  ylabel: str,
                                  x_ticks_labels: List[float],
                                  group_name: str,
                                  left_margin=False):
        data = list(reversed(data))
        x_ticks_labels = list(reversed(x_ticks_labels))

        self._print_h_bar_graph(html,
                                xs=data,
                                ys=list(range(len(data))),
                                xlabel=ylabel,
                                ylabel=xlabel,
                                title=f"Distribution of {group_name} across {xlabel}",
                                y_tick_lables=x_ticks_labels,
                                left_margin=left_margin)

    def _get_geolist_from_sample(self, sample: List[Ip_stats])\
            -> List[Tuple[str,float]]:
        # returns List of tuples (location, percent of that location in sample)
        #   location is weighted by session count

        geoloc = {}
        val_sum = 0

        for ip_stat in sample:
            if ip_stat.geolocation in ["", "Unknown", " "]:
                ip_stat.update_geolocation()

            value = geoloc.get(ip_stat.geolocation, 0)
            value += ip_stat.sessions_num  # weight the value by number of sessions
            geoloc[ip_stat.geolocation] = value
            val_sum += ip_stat.sessions_num

        geoloc = sorted(map(lambda x, s=val_sum: (x[0], 100 * x[1] / s),
                                geoloc.items()),
                            key=lambda x: x[1],
                            reverse=True)
        return geoloc

    def _test_geolocation(self,
                          html: Html_maker,
                          geoloc_sample_size: int,
                          repetitions: int = 5,
                          selected: bool = False):

        # now olnly for human users
        def filter_f(stat: Ip_stats) -> bool:
            return stat.sessions_num <= 50
        data: List[Ip_stats] = list(filter(filter_f, self.people.stats.values()))

        samples: List[List[Ip_stats]] = []
        sample_size = min(len(data),
                          geoloc_sample_size)

        for _ in range(repetitions):
            if len(data) > sample_size:
                samples.append(random.sample(data, sample_size))
            else:
                samples.append(data)

        # geolocation
        timer = Ez_timer("geolocations", verbose=self.err_msg)

        geoloc_stats = []
        for i, sample in enumerate(samples):
            timer2 = Ez_timer(f"geolocaion {i+1}", verbose=False)
            geoloc_stats.append(self._get_geolist_from_sample(sample))
            timer2.finish(self.err_msg)

        timer.finish(self.err_msg)

        # Printing
        selected = "selected" if selected else ""

        html.append("<h3>Estimated locations</h3>")
        button_names = [f"geoloc{i}" for i in range(1, repetitions + 1)]
        uniq_classes = html.print_selection(
            button_names,
            [["selectable", selected]]*repetitions)

        # print geolocation
        html.append(f'<div class="flex-align-start">')
        for i in range(repetitions):
            html.append(
                f'<div class="selectable {selected} {uniq_classes[i]}">')
            self.print_countries_bars(html,
                                      geoloc_stats[i],
                                      "Geolocation",
                                      left_margin=True,
                                      max_size=20)
            html.append("</div>")
        html.append("</div>")

    def _print_countries_stats(self,
                               html: Html_maker,
                               sample_size: int,
                               selected: bool = False):
        # now olnly for human users

        if sample_size <= 0:
            return

        # Filter out ips with number of sessions greater than 50
        def filter_f(stat: Ip_stats) -> bool:
            return stat.sessions_num <= 50
        sample: List[Ip_stats] = list(filter(filter_f, self.people.stats.values()))

        sample_size = min(len(sample),
                          sample_size)

        if len(sample) > sample_size:
            sample = random.sample(sample, sample_size)
        else:
            sample_size = len(sample)

        # geolocation
        if self.err_msg:
            timer = Ez_timer("geolocation")

        geoloc_stats = self._get_geolist_from_sample(sample)

        if self.err_msg:
            timer.finish()

        # making html
        selected = "selected" if selected else ""

        html.append("<h3>Estimated locations</h3>")
        uniq_classes = html.print_selection(
            ["Geoloc table", "Geoloc graph"],
            [[selected]]*2)

        # geolocation table
        def content_iter(data: List[Tuple[str, float]]):
            rank = 1
            for country, value in data:
                yield [rank, country, round(value, 2)]
                rank += 1

        html.append('<div class="flex-align-start">')
        html.append(
            f'<div class="selectable {selected} {uniq_classes[0]} flex-col-center">')
        html.append(make_table("Most frequent geolocations",
                                ["Rank", "Geolocation", "Percetns"],
                                content_iter(geoloc_stats)))
        html.append('<a href="http://www.geoplugin.com/geolocation/">IP Geolocation</a>'
                    ' by <a href="http://www.geoplugin.com">geoPlugin</a>\n</div>')

        # geolocation graph
        html.append(
            f'<div class="selectable {selected} {uniq_classes[1]} flex-col-center">')
        self.print_countries_bars(html,
                                    geoloc_stats,
                                    "Geolocation",
                                    left_margin=True,
                                    max_size=10)
        html.append('<a href="http://www.geoplugin.com/geolocation/">IP Geolocation</a>'
                    ' by <a href="http://www.geoplugin.com">geoPlugin</a>\n</div>')
        html.append('</div>')

    def print_countries_bars(self,
                             html: Html_maker,
                             sorted_data: List[Tuple[str, float]],
                             title: str,
                             left_margin: bool = False,
                             max_size: Optional[int] = None):
        sorted_country_names = []
        sorted_country_percents = []
        other = 0

        if max_size is not None and len(sorted_data) > max_size:
            other = sum(map(lambda x: x[1], sorted_data[max_size:]))
            sorted_data = sorted_data[:max_size]

        for name, percent in sorted_data:
            sorted_country_names.append(name)
            sorted_country_percents.append(percent)

        if other > 0:
            sorted_country_names.append("other")
            sorted_country_percents.append(other)

        self._print_h_bar_graph(html,
                                sorted_country_percents,
                                list(range(len(sorted_country_names))),
                                'Percents',
                                '',
                                title,
                                sorted_country_names,
                                left_margin)

    def _print_h_bar_graph(self, html: Html_maker, xs, ys, xlabel, ylabel,
                           title, y_tick_lables, left_margin: bool = False):
        # set height of the graph
        x, y = plt.rcParams['figure.figsize']
        y = y * len(ys) / 12
        if len(ys) < 10:
            y += 3
        plt.rcParams['figure.figsize'] = (x, y)

        fig, ax = plt.subplots()
        ax.ticklabel_format(axis='x', style='sci',
                            scilimits=(-4, 4), useOffset=False)
        ax.barh(y=ys, width=xs, align='center')

        for i, x in enumerate(xs):
            plt.annotate(str(round(x, 2)),
                         (x, i),
                         horizontalalignment='left',
                         verticalalignment='center')
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)

        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_yticks(ys)
        ax.set_yticklabels(y_tick_lables)
        if left_margin:
            plt.subplots_adjust(left=0.25)

        with io.StringIO() as f:
            plt.savefig(f, format="svg")
            html.append(f.getvalue())
        plt.clf()
        plt.close(fig)
        plt.rcParams['figure.figsize'] = plt.rcParamsDefault['figure.figsize']

    def make_histogram(self, file_name:str, selected:str = ""):
        # For people only!!

        with open(f"{os.path.dirname(__file__)}/hist.js", "r") as f:
            js = f.read()
        template = "<html><head><style>{css}</style> <script>{js}</script></head>\n<body>\n{content}\n</body>\n</html>"
        html: Html_maker = Html_maker(template, js = js)

        html.append("<h1>Histograms</h1>")

        for year in sorted(self.year_stats.keys()):
            session_data = []
            request_data = []
            self._switch_years(year)

            stats = self.people.stats.values()
            for stat in stats:
                session_data.append(stat.sessions_num)
                request_data.append(stat.requests_num)

            html.append(f"<h2>Year {year}</h2>")
            selected = "selected" if selected else ""

            # sessions
            html.append("<h3>Session histogram</h3>")
            uniq_classes = html.print_selection(["Full histogram", "Detailed histogram", "Table"],
                                                [[selected]]*3)
            html.append("<div class='flex-align-start'>")

            self._print_histogram_graphs(html=html,
                                        data=session_data,
                                        delims=[2, 5, 10, 50, 100, 1000],
                                        bins=300,
                                        cutoff_for_detail=300,
                                        xlabel="Session count",
                                        uniq_classes=uniq_classes)
            html.append("</div>")
        
            # requests
            html.append("<h3>Requests histogram</h3>")
            uniq_classes = html.print_selection(["Full histogram", "Detailed histogram", "Table"],
                                                [[selected]]*3)
            html.append("<div class='flex-align-start'>")

            self._print_histogram_graphs(html=html,
                                        data=request_data,
                                        delims=[2, 5, 10, 50, 100, 1000, 10000],
                                        bins=500,
                                        cutoff_for_detail=800,
                                        xlabel="Request count",
                                        uniq_classes=uniq_classes,
                                        selected=selected)
            html.append("</div>")

            # top users
            self._print_most_frequent(
                html,
                sorted(stats, key=lambda x: x.requests_num, reverse=True),
                sorted(stats, key=lambda x: x.sessions_num, reverse=True),
                bots=False,
                selected=selected,
                host_name=False)

        plt.close('all')

        with open(file_name, "w") as f:
            f.write(html.html())
    

    def _print_histogram_graphs(self,
                              html: Html_maker,
                              data: List[int],
                              delims: List[int],
                              bins: int,
                              cutoff_for_detail: int,
                              xlabel: str,
                              uniq_classes=List[str],
                              selected=""):

            _, ax = plt.subplots()
            ax.hist(data, bins=bins, log=True, histtype='stepfilled')
            ax.set_xlabel(xlabel)
            ax.set_ylabel("Ip address count")
            ax.set_title("Full histogram")

            html.append(f"<div class='{uniq_classes[0]} selectable {selected}'>")
            with io.StringIO() as f:
                plt.savefig(f, format="svg")
                html.append(f.getvalue())
            html.append("</div>")

            ax.set_xlim(left=-10, right=cutoff_for_detail)
            ax.set_title("Detailed histogram")

            html.append(f"<div class='{uniq_classes[1]} selectable {selected}'>")
            with io.StringIO() as f:
                plt.savefig(f, format="svg")
                html.append(f.getvalue())
            plt.clf()
            html.append("</div>")

            self.splited_data_info(data, delims, html, uniqe_class=uniq_classes[2], selected=selected)


    def splited_data_info(self, 
                          data: List[int], 
                          delims: List[int], 
                          html: Optional[Html_maker]=None, 
                          data_name="ip addresses",
                          uniqe_class:str="",
                          selected="") -> List[List[int]] : 
        # splits values in data into categories: i-th category contains values, such that
        #   delims[i-1] <= values < delims[i], 0th categoty is min val <= values < delims[0],
        #   last category is delims[-1] <= values <= max val
        # if html is given appends a small table about the splitted data

        categories = [ [] for _ in range(len(delims) + 1) ]
        categories_sums = [ 0 for _ in range(len(delims) + 1) ]

        for val in data:
            for i in range(len(delims)):

                if val < delims[i]:
                    categories[i].append(val)
                    categories_sums[i] += val
                    break
            else:
                categories[-1].append(val)
                categories_sums[-1] += val


        if html is None:
            return categories

        # here follows the small table
        tot = sum(categories_sums)
        content = []
        prev = 0

        for i in range(len(delims)):
            content.append(
                [f"{prev} to {delims[i]-1}", 
                 categories_sums[i], 
                 round(100*categories_sums[i]/tot, 1),
                 len(categories[i]), #unique ip addresess
                 round(100*len(categories[i])/len(data), 1)] #unique ip addresess in %
            )
            prev = delims[i]

        content.append(
            [f"Above {delims[-1]}", categories_sums[-1],
             round(100*categories_sums[-1]/tot, 1), len(categories[-1]),
             round(100*len(categories[-1])/len(data), 1)] 
        )
        content.append(
            ["Total", tot, 100 , len(data), 100] 
        )
        
        html.append(f"<div class='{uniqe_class} selectable {selected}'>")
        html.append(make_table(f"Categoriezed {data_name}",
                               ["Range  [from, to]", "Sum", "Sum [%]", "Unique IPs", "Unique IPs [%]"],
                               content))
        html.append("</div>")
        return categories