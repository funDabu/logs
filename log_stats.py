from collections import Counter
import sys
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


"""
========== CONSTANTS ==========
"""
from constants import LOG_DT_FORMAT, DT_FORMAT, DATE_FORMAT, MONTHS, DAYS

BOT_URL_REGEX = r"(http\S+?)[);]"
RE_PROG_BOT_URL = re.compile(BOT_URL_REGEX)

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
========== STATISTICS ==========
"""

def strp_date(date: str, format: str) -> datetime.date:
    dt = datetime.datetime.strptime(date, format)
    return dt.date()

def get_bot_url(user_agent: str) -> str:
    # if "user agent" field of the log entry doesn't contain
    #   bot's url, returns empty string
    match = RE_PROG_BOT_URL.search( user_agent)
    if match is None:
        return ""
    return match.group(1)


def determine_bot(entry:Log_entry, *args: Callable[[Log_entry], bool]) -> Tuple[bool, str]:
    # returns: - [True, bot_url] if stat is classified as bot based on url in user_agent,
    #          - [True, ""] when bot classified based on predicate in *args,
    #          - [False, ""]  otherwise

    match = RE_PROG_BOT_URL.search(entry.user_agent)
    if match is not None:
        return (True, match.group(1))

    for func in args:
        if func(entry):
            return (True, "")
    
    return (False, "")


class Ip_stats:
    first_api_req_ts = None
    free_geolocations = 110  # www.geoplugin.net api oficial limit is 120 requsts/min
    session = requests.Session()
    re_prog_bot_url = re.compile(BOT_URL_REGEX)

    __slots__ = ("ip_addr", "host_name", "geolocation", "bot_url",
                 "is_bot", "requests_num", "sessions_num", "datetime")

    def __init__(self, entry:Log_entry, is_bot:Optional[bool]=None,
                 bot_url="", json:Optional[str]=None) -> None:

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

    def update_host_name(self, precision: int = 3) -> None:
        try:
            hostname = socket.gethostbyaddr(self.ip_addr)[0]
            hostname = hostname.rsplit('.')
            if len(hostname) > precision:
                hostname = hostname[-precision:]

            self.host_name = '.'.join(hostname)

        except:
            self.host_name = "Unknown"

    def add_entry(self, entry: Log_entry) -> int:
        # <entry> is line from log parsed with <parse_log_entry> function
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
        self._safer_geolocation()

    def _safer_geolocation(self):
        # sleeps 2 sec after every 3 requests (~ 90 req / min)
        self._geolocate(3, lambda: 2)

    def _efficient_geolocation(self):
        # do not use !! You will get blacklisted
        self._geolocate(110, lambda: max(
            0, (60 + Ip_stats.first_api_req_ts - time.time())))

    def _geolocate(self, token_max, get_sleep_time):
        if Ip_stats.first_api_req_ts is None or\
           time.time() - Ip_stats.first_api_req_ts > 60:
            Ip_stats.first_api_req_ts = time.time()
            Ip_stats.free_geolocations = token_max

        if not Ip_stats.free_geolocations:
            # print(f"sleep for {get_sleep_time()}", file=sys.stderr)
            time.sleep(get_sleep_time())
            Ip_stats.first_api_req_ts = time.time()
            Ip_stats.free_geolocations = token_max

        Ip_stats.free_geolocations -= 1
        # print(f"calling api", file=sys.stderr)
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


def anotate_bars(xs: List[float], ys: List[float], labels: List[int], rotation: int):
    for i, x in enumerate(xs):
        plt.annotate(str(labels[i]), (x, ys[i]),
                     rotation=rotation, horizontalalignment='center')


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
                    year=None):
        if year is not None:
            self._switch_years(year)

        html: Html_maker = Html_maker()
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
        self._print_day_distribution(html, True, selected)
        self._print_week_distribution(html, True, selected)
        self._print_month_distributions(html, True, selected)

    def _print_overview(self,
                        html: Html_maker,
                        header_str: str,
                        req_sorted_stats: List[Ip_stats]) -> None:
        html.append(make_table("Overview",
                               [header_str],
                               [[str(len(req_sorted_stats))]]
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


# TODO: prepsat na jeden
    def _people_iter(self, data: List[Ip_stats], n: int, host_name=True):
        i = 0
        n = min(n, len(data))
        while i < n:
            ip_stat = data[i]
            if host_name:
                ip_stat.update_host_name()
            if not ip_stat.geolocation:
                ip_stat.update_geolocation()
            yield [f"{i + 1}",
                    ip_stat.ip_addr,
                    ip_stat.host_name,
                    ip_stat.geolocation,
                    ip_stat.requests_num,
                    ip_stat.sessions_num
                    ]
            i += 1
    
    def _bots_iter(self, data: List[Ip_stats], n: int, host_name=True):
        i = 0
        n = min(n, len(data))
        while i < n:
            ip_stat = data[i]
            if host_name:
                ip_stat.update_host_name()
            yield [f"{i + 1}",
                    ip_stat.bot_url,
                    ip_stat.host_name,
                    ip_stat.requests_num,
                    ip_stat.sessions_num
                    ]
            i += 1

    def _print_most_frequent(self,
                             html: Html_maker,
                             req_sorted_stats: List[Ip_stats],
                             sess_sorted_stats: List[Ip_stats],
                             bots,
                             selected="",
                             host_name=True):

        html.append('<h3>Most frequent</h3>\n<label>Select:</label>')

        uniq_classes = html.print_sel_buttons(["session table", "requests table"],
                                              [[selected]] * 2)
        html.append("<div>")

        if bots:
            group_name = "bots"
            header = ["Rank", "Bot's url", "Host name",
                      "Requests count", "Sessions count"]
            content_iter = self._bots_iter
        else:
            group_name = "human users"
            header = ["Rank", "IP address", "Host name",
                      "Geolocation", "Requests count", "Sessions count"]
            content_iter = self._people_iter

        html.append(make_table(f"Most frequent {group_name} by number of sessions",
                               header,
                               content_iter(sess_sorted_stats, 20, host_name),
                               None,
                               ["selectable", selected, uniq_classes[0]]))

        html.append(make_table(f"Most frequent {group_name} by number of requests",
                               header,
                               content_iter(req_sorted_stats, 20, host_name),
                               None,
                               ["selectable", selected, uniq_classes[1]]))
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
            "<h3>Distribution of across hours of day</h3>\n<label>Selected:</label>")
        uniq_classes = html.print_sel_buttons(
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
            "<h3>Distributions across week days</h3>\n<label>Select:</label>")
        uniq_classes = html.print_sel_buttons(
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
            "<h3>Distributions accross months</h3>\n<label>Select:</label>")
        uniq_classes = html.print_sel_buttons(
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

        html.append("<h3>Estimated locations</h3>\n<label>Select:</label>")
        button_names = [f"geoloc{i}" for i in range(1, repetitions + 1)]
        uniq_classes = html.print_sel_buttons(
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

        data = self.people

        sample: List[Ip_stats] = list(data.stats.values())
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

        html.append("<h3>Estimated locations</h3>\n<label>Select:</label>")
        uniq_classes = html.print_sel_buttons(
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

    def print_histogram(self, file_name: str):
        # For people only!!

        with open("hist.js", "r") as f:
            js = f.read()
        template = "<html><head><style>{css}</style> <script>{js}</script></head>\n<body>\n{content}\n</body>\n</html>"
        html = Html_maker(template, js = js)


        for year in sorted(self.year_stats.keys()):
            session_data = []
            request_data = []
            self._switch_years(year)

            stats = self.people.stats.values()
            for stat in stats:
                session_data.append(stat.sessions_num)
                request_data.append(stat.requests_num)

            html.append(f"<h2>Year {year}</h2>")

            # sessions
            html.append("<h3>Session histogram</h3>")
            s_delims = [1, 2, 5, 10, 50, 100, 1000]
            s_bins = 150

            _, ax = plt.subplots()
            # ax.set_xticks(sorted(set([1000*i for i in range(7)] + s_delims)))
            ax.hist(session_data, bins=s_bins, log=True)

            with io.StringIO() as f:
                plt.savefig(f, format="svg")
                html.append(f.getvalue())
            plt.clf()

            _, ax = plt.subplots()
            sess_lesser_data = self.splited_data_info(session_data, [200])[0]
            ax.hist(sess_lesser_data, bins=s_bins, log=True)

            with io.StringIO() as f:
                plt.savefig(f, format="svg")
                html.append(f.getvalue())
            plt.clf()

            self.splited_data_info(session_data, s_delims, html)


        
            # requests
            html.append("<h3>Requests histogram</h3>")
            r_delims = [1, 2, 5, 10, 50, 100, 1000, 10000]
            r_bins = 300

            _, ax = plt.subplots()
            # ax.set_xticks(sorted(set([50000*i for i in range(5)] + r_delims)))
            ax.hist(request_data, bins=r_bins, log=True)

            with io.StringIO() as f:
                plt.savefig(f, format="svg")
                html.append(f.getvalue())
            plt.clf()

            _, ax = plt.subplots()
            req_lesser_data = self.splited_data_info(request_data, [600])[0]
            ax.hist(req_lesser_data, bins=s_bins, log=True)

            with io.StringIO() as f:
                plt.savefig(f, format="svg")
                html.append(f.getvalue())
            plt.clf()

            self.splited_data_info(request_data, r_delims, html)

            # top users
            self._print_most_frequent(
                html,
                sorted(stats, key=lambda x: x.requests_num, reverse=True),
                sorted(stats, key=lambda x: x.sessions_num, reverse=True),
                bots=False,
                selected="selected",
                host_name=False)

        plt.close('all')

        

        with open(file_name, "w") as f:
            f.write(html.html())

    def splited_data_info(self, 
                          data: List[int], 
                          delims: List[int], 
                          html: Optional[Html_maker]=None, 
                          data_name="Data") -> List[List[int]] : 
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

        content = [ 
            [f"Less than {delims[i]}", categories_sums[i],
             round(100*categories_sums[i]/tot, 1), len(categories[i]),
             round(100*len(categories[i])/len(data), 1)] 
                for i in range(len(delims))
        ]
        content.append(
            [f"Above {delims[-1]}", categories_sums[-1],
             round(100*categories_sums[-1]/tot, 1), len(categories[-1]),
             round(100*len(categories[-1])/len(data), 1)] 
        )
        content.append(
            ["Total", tot, 100 , len(data), 100] 
        )
        
        html.append(make_table(f"{data_name} splited",
                               ["Category", "Sum", "Sum [%]", "Unique IPs", "Unique IPs [%]"],
                               content))
        return categories