from collections import Counter
import sys
import socket
import datetime
import matplotlib.pyplot as plt
import requests
import time
import json

from logs.parser.log_parser import Log_entry, parse_entry_with_regex, regex_parser
from logs.statistics.ez_timer import Ez_timer
from logs.statistics.geoloc_db import GeolocDB

from typing import List, TextIO, Optional, Tuple, Dict, Set, Callable, NamedTuple


from logs.structures.constants import LOG_DT_FORMAT, DT_FORMAT, DATE_FORMAT
from logs.statistics.constants import RE_PATTERN_SIMPLE_IPV4, RE_PATTERN_BOT_URL,\
                                      RE_PATTERN_BOT_USER_AGENT, SESSION_DELIM

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

def simple_ipv4_check(ip: str) -> bool:
    """Non-exhaustivly tests if `ip` is already a valid IPv4

    Returns
    -------
    bool
        - `True` if `ip` is valid IPv4 
        - `False` otherwise
    """
    return RE_PATTERN_SIMPLE_IPV4.search(ip) is not None

def host_to_ip(host: str) -> Tuple[bool, str]:
    """Tries to relove `host` and return the result

    Returns
    -------
    Tuple[bool, str]
        - `(True, <resolved ip>)` if IPv4 could be resolved
        - `(False, host)` if IPv4 couldn't be resolved
    """   
    try:
        addr = socket.gethostbyname(host)
        return (True, addr)
    except:
        return (False, host)

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
    last_geoloc_ts = time.time() # time stamp of the last call to geolocation API
    session = requests.Session() # for geolocation API

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
        self.geolocation = "Unresolved"
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
    
    def ensure_valid_ip_address(self, ip_map: Optional[Dict[str, str]] = None) -> bool:
        """Does a simple incomplete validation of `self.ip_addr`.
        If `self.ip_addr` in not an IP address,
        than it might be a domain name, 
        so a DNS lookup will be made to find corresponding IP address
        and `self.ip_addr` will be set accordingly.

        If `ip_map` is given and `self.ip_addr` is one of its keys,
        then `self.ip_address` is set to the corresponding value in the map
        at the begining and the method returns.

        Parameters
        ----------
        ip_map: Dict[str, str], optional
            memo for invalid ips,
            maps invalid ip to corresponding valid ip

        Returns
        -------
        bool
            - `True` if `self.ip_addr` probably contains valid ip address
              or was fixed to a valid ip.
            - `False` if `self.ip_addr` is not valid
              and the address could not be resolved
        """        
        if simple_ipv4_check(self.ip_addr):
            return True
        
        if ip_map is not None:
            ip = ip_map.get(self.ip_addr)

            if ip is not None:
                self.host_name = self.ip_addr
                self.ip_addr = ip
                return True
        
        valid, ip = host_to_ip(self.ip_addr)

        if ip_map is not None:
            ip_map[self.ip_addr] = ip

        if valid:
            self.host_name = self.ip_addr
            self.ip_addr = ip
        
        return valid

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

    def update_geolocation(self,  database: GeolocDB):
        if database is None:
            self.geolocate_with_api()
            return

        val = database.get_geolocation(self.ip_addr)
        if val is not None:
            self.geolocation, _ = val
            return

        self.geolocate_with_api()
        database.insert_geolocation(self.ip_addr, self.geolocation)
    
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
    """Data structure to store statistical informations about one category 
    of entries (either bots or people)

    Attributes
    ----------
    stats: Dict[str, Ip_stats]
        maps IPv4 as string to Ip_stats object
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

    def __init__(self, js: Optional[Dict]=None):
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


class Daily_stats(NamedTuple):
    ips: Set[str]
    requests: int
    sessions: int

class Log_stats:
    """
    Attributes
    ----------
    bots: Stat_struct
        stores informations about bots for current year
    poeple: Stat_struct
        stores informations about humna users for current year
    current_year: int, optional
    daily_data: Dict[datetime.date, Daily_stats]
        maps dates to a named tuples (<unique ips>, <number of requests>, <number of human sessions>)
        the tuple contains information related to the given date
        this information is used for making picture overview
    year_stats: Dict[int, Tuple(Stat_struct, Stat_struct)]
        maps years to tuples (<Stat_struct for bots>, <Stat_struct for people>)
    config_f: str, optional
        path to a blacklist file containing ip addressed considered as bots
    bots_set: Set[str]
        contains ip adresses from config_f
    """
    def __init__(self, input: Optional[TextIO] = None, err_msg=False, config_f=None):
        self.bots = Stat_struct()
        self.people = Stat_struct()
        self.err_msg = err_msg
        self.daily_data: Dict[datetime.date, Daily_stats] = {}
        self.year_stats: Dict[int, Tuple(Stat_struct, Stat_struct)] = {}
        self.current_year = None

        if config_f is not None:
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
            return {dt.__format__(DATE_FORMAT): (list(data.ips), data.requests, data.sessions)
                        for dt, data in self.daily_data.items()}
        
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
            self.daily_data = {strp_date(d, DATE_FORMAT): Daily_stats(set(ips), r, s)
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

    def resolve_and_group_ips(self, ip_map: Dict[str, str] = {}) -> None:
        """Resolves ip address for all data in year_data
        and merges same ips together

        Parameters
        ----------
        ip_map: Dict[str, str], optional
            maps invalid adress to resolved address
        """
        if self.err_msg:
            timer = Ez_timer("IPs resolving and merging")

        for year, vals in self.year_stats.items():
            bots, people = vals[0], vals[1]

            self._resolve_and_group_ips_from_stat_structs(bots, ip_map)
            self._resolve_and_group_ips_from_stat_structs(people, ip_map)
            self.year_stats[year] = (bots, people)

        # resolve and merge self.daily_data
        # now all ips were already resoved and invalid are saved in ip_map
        for date, data in self.daily_data.items():
            ips: Set[str] = data.ips
            grouped_ips: Set[str] = set()

            for ip in ips:
                resolved = ip_map.get(ip)
                grouped_ips.add(ip if resolved is None else resolved)            
            self.daily_data[date] = Daily_stats(grouped_ips, data.requests, data.sessions)

        if timer is not None:
            timer.finish()
                
    def _resolve_and_group_ips_from_stat_structs(
            self,
            stat_struct: Stat_struct,
            ip_map: Optional[Dict[str,str]] = None)\
                -> None:
        """Resolves ip address in `stat_struct`
        and merges data for same ips together

        Parameters
        ----------
        stat_struct: Stat_struct
            Stat_struct which will be modified
        ip_map: Dict[str, str], optional
            maps invalid adress to resolved address
        """
        grouped_stats: Dict[str, Ip_stats] = {}
        
        for stat in stat_struct.stats.values():
            stat.ensure_valid_ip_address(ip_map)
            ip = stat.ip_addr

            grouped = grouped_stats.get(ip)
            stat.requests_num += 0 if grouped is None else grouped.requests_num
            stat.sessions_num += 0 if grouped is None else grouped.sessions_num
            grouped_stats[ip] = stat
        
        stat_struct.stats = grouped_stats
               
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

        is_bot, bot_url = determine_bot(
            entry,
            lambda x: x.ip_addr in self.bots_set,
            lambda x: RE_PATTERN_BOT_USER_AGENT.search(x.user_agent) is not None)

        stat_struct = self.bots if is_bot else self.people

        ip_stat = stat_struct.stats.get(entry.ip_addr)
        if ip_stat is None:
            ip_stat = Ip_stats(entry, is_bot, bot_url)
            
        new_sess = ip_stat.add_entry(entry)
        # ^: 1 if new session was created, 0 otherwise

        stat_struct.stats[entry.ip_addr] = ip_stat
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
        self.daily_data[date] = Daily_stats(ip_addrs, req_num + 1, sess_num)

    def _switch_years(self, year: int):
        if self.current_year is not None:
            self.year_stats[self.current_year] = (self.bots, self.people)

        self.current_year = year
        self.bots, self.people =\
            self.year_stats.get(year, (Stat_struct(), Stat_struct()))
    
    