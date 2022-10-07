from typing import List, TextIO, Optional, Tuple, Dict, Set
from collections import Counter
import sys
import socket
import datetime
from xmlrpc.client import DateTime
import matplotlib.pyplot as plt
import io
from html_maker import Html_maker, make_table
import random
import requests
import time
from log_parser import Log_entry, parse_log_entry


"""
========== CONSTANTS ==========
"""

SESSION_DELIM = 1  # in minutes

TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"

MONTHS = ["Error", "Jan", "Feb", "Mar", "Apr", "May",
          "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = ["Mon", "Tue", "Wed", "Thr", "Fri", "Sat", "Sun"]
CCTLDS = {  # coutry code top level domains
    "ac": "Ascension Island",
    "ad": "Andorra",
    "ae": "United Arab Emirates",
    "af": "Afghanistan",
    "ag": "Antigua and Barbuda",
    "ai": "Anguilla",
    "al": "Albania",
    "am": "Armenia",
    "an": "Netherlands Antilles ",
    "ao": "Angola",
    "aq": "Antarctic",
    "ar": "Argentina",
    "as": "American Samoa",
    "at": "Austria",
    "au": "Australia",
    "aw": "Aruba",
    "ax": "Åland Islands ",
    "az": "Azerbaijan",
    "ba": "Bosnia and Herzegovina",
    "bb": "Barbados",
    "bd": "Bangladesh",
    "be": "Belgium",
    "bf": "Burkina Faso",
    "bg": "Bulgaria",
    "bh": "Bahrain",
    "bi": "Burundi",
    "bj": "Benin",
    "bl": "Saint",
    "bm": "Bermuda",
    "bn": "Brunei",
    "bo": "Bolivia",
    "br": "Brazil",
    "bq": "Bonaire",
    "bs": "Bahamas",
    "bt": "Bhutan",
    "bv": "Bouvet Island ",
    "bw": "Botswana",
    "by": "Belarus",
    "bz": "Belize",
    "ca": "Canada",
    "cc": "Cocos Islands",
    "cd": "Democratic Republic of the Congo",
    "cf": "Central African Republic",
    "cg": "Republic of the Congo",
    "ch": "Switzerland",
    "ci": "Côte d",
    "ck": "Cook Islands",
    "cl": "Chile",
    "cm": "Cameroon",
    "cn": "China",
    "co": "Colombia",
    "cr": "Costa Rica",
    "cs": "Czechoslovakia ",
    "cu": "Cuba",
    "cv": "Cape Verde",
    "cw": "Curaçao",
    "cx": "Christmas Island",
    "cy": "Cyprus",
    "cz": "Czech Republic",
    "dd": "German Democratic Republic ",
    "de": "Germany",
    "dj": "Djibuti",
    "dk": "Denmark",
    "dm": "Dominica",
    "do": "Dominican Republic",
    "dz": "Algeria",
    "ec": "Ecuador",
    "ee": "Estonia",
    "eg": "Egypt",
    "eh": "Western Sahara ",
    "er": "Eritrea",
    "es": "Spain",
    "et": "Ethiopia",
    "eu": "European Union",
    "fi": "Finland",
    "fj": "Fiji",
    "fk": "Falkland Islands",
    "fm": "Micronesia",
    "fo": "Faroe",
    "fr": "France",
    "ga": "Gabon",
    "gb": "United Kingdom ",
    "gd": "Grenada",
    "ge": "Georgia",
    "gf": "French Guiana",
    "gg": "Guernsey",
    "gh": "Ghana",
    "gi": "Gibraltar",
    "gl": "Greenland",
    "gm": "Gambia",
    "gn": "Guinea",
    "gp": "Guadeloupe",
    "gq": "Equatorial Guinea",
    "gr": "Greece",
    "gs": "South Georgia and the South Sandwich Islands",
    "gt": "Guatemala",
    "gu": "Guam",
    "gw": "Guinea",
    "gy": "Guyana",
    "hk": "Hong Kong",
    "hm": "Heard Island and McDonald Islands",
    "hn": "Honduras",
    "hr": "Croatia",
    "ht": "Haiti",
    "hu": "Hungary",
    "id": "Indonesia",
    "ie": "Ireland",
    "il": "Israel",
    "im": "Isle of Man",
    "in": "India",
    "io": "British Indian Ocean Territory",
    "iq": "Iraq",
    "ir": "Iran",
    "is": "Iceland",
    "it": "Italy",
    "je": "Jersey",
    "jm": "Jamaica",
    "jo": "Jordan",
    "jp": "Japan",
    "ke": "Kenya",
    "kg": "Kyrgyzstan",
    "kh": "Cambodia",
    "ki": "Kiribati",
    "km": "Comoros",
    "kn": "St. Kitts and Nevis",
    "kp": "North Korea",
    "kr": "South Korea",
    "kw": "Kuwait",
    "ky": "Cayman Islands",
    "kz": "Kazakhstan",
    "la": "Laos",
    "lb": "Lebanon",
    "lc": "St. Lucia",
    "li": "Liechtenstein",
    "lk": "Sri Lanka",
    "lr": "Liberia",
    "ls": "Lesotho",
    "lt": "Lithuania",
    "lu": "Luxembourg",
    "lv": "Latvia",
    "ly": "Libya",
    "ma": "Marocco",
    "mc": "Monaco",
    "md": "Moldova",
    "me": "Montenegro",
    "mf": "Saint Martin",
    "mg": "Madagascar",
    "mh": "Marshall Islands",
    "mk": "Macedonia",
    "ml": "Mali",
    "mm": "Myanmar",
    "mn": "Mongolia",
    "mo": "Macau",
    "mp": "Northern Mariana Islands",
    "mq": "Martinique",
    "mr": "Mauritania",
    "ms": "Montserrat",
    "mt": "Malta",
    "mu": "Mauritius",
    "mv": "Maldives",
    "mw": "Malawi",
    "mx": "Mexico",
    "my": "Malaysia",
    "mz": "Mozambique",
    "na": "Namibia",
    "nc": "New Caledonia",
    "ne": "Niger",
    "nf": "Norfolk Island",
    "ng": "Nigeria",
    "ni": "Nicaragua",
    "nl": "Netherlands",
    "no": "Norway",
    "np": "Nepal",
    "nr": "Nauru",
    "nu": "Niue",
    "nz": "New Zealand",
    "om": "Oman",
    "pa": "Panama",
    "pe": "Peru",
    "pf": "French Polynesia",
    "pg": "Papua New Guinea",
    "ph": "Philippines",
    "pk": "Pakistan",
    "pl": "Poland",
    "pm": "Saint Pierre and Miquelon",
    "pn": "Pitcairn Islands",
    "pr": "Puerto Rico",
    "ps": "Palestine",
    "pt": "Portugal",
    "pw": "Palau",
    "py": "Paraguay",
    "qa": "Qatar",
    "re": "Réunion",
    "ro": "Romania",
    "rs": "Serbia",
    "ru": "Russia",
    "rw": "Rwanda",
    "sa": "Saudi Arabia",
    "sb": "Solomon Islands",
    "sc": "Seychelles",
    "sd": "Sudan",
    "se": "Sweden",
    "sg": "Singapore",
    "sh": "St. Helena",
    "si": "Slovenia",
    "sj": "Svalbard and Jan Mayen ",
    "sk": "Slovakia",
    "sl": "Sierra Leone",
    "sm": "San Marino",
    "sn": "Senegal",
    "so": "Somalia",
    "sr": "Suriname",
    "ss": "South Sudan",
    "st": "São Tomé and Príncipe",
    "su": "Soviet Union ",
    "sv": "El Salvador",
    "sx": "Sint Maarten",
    "sy": "Syria",
    "sz": "Swaziland",
    "tc": "Turks and Caicos Islands",
    "td": "Chad",
    "tf": "French Southern and Antarctic Lands",
    "tg": "Togo",
    "th": "Thailand",
    "tj": "Tajikistan",
    "tk": "Tokelau",
    "tl": "Timor",
    "tm": "Turkmenistan",
    "tn": "Tunisia",
    "to": "Tonga",
    "tp": "Timor",
    "tr": "Turkey",
    "tt": "Trinidad and Tobago",
    "tv": "Tuvalu",
    "tw": "Taiwan",
    "tz": "Tanzania",
    "ua": "Ukraine",
    "ug": "Uganda",
    "uk": "United Kingdom",
    "um": "United States Minor Outlying Islands ",
    "us": "United States",
    "uy": "Uruguay",
    "uz": "Uzbekistan",
    "va": "Vatican City",
    "vc": "St. Vincent and the Grenadines",
    "ve": "Venezuela",
    "vg": "Britische Virgin Islands",
    "vi": "United States Virgin Islands",
    "vn": "Vietnam",
    "vu": "Vanuatu",
    "wf": "Wallis and Futuna ",
    "ws": "Samoa",
    "ye": "Yemen",
    "yt": "Mayotte ",
    "yu": "Yugoslavia ",
    "za": "South Africa",
    "zm": "Zambia",
    "zr": "Zaire ",
    "zw": "Zimbabwe",
}

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


class Ip_stats:
    first_api_req_ts = None
    free_geolocations = 110  # www.geoplugin.net api oficial limit is 120 requsts/min
    session = requests.Session()

    __slots__ = ("ip_addr", "host_name", "geolocation", "bot_url",
                 "is_bot", "requests_num", "sessions_num", "date")

    def __init__(self, entry: Log_entry, bot_url=None) -> None:
        self.ip_addr = entry.ip_addr
        self.host_name = "Unresolved"
        self.geolocation = ""

        if bot_url is None:
            bot_url = entry.get_bot_url()
        self.bot_url = bot_url
        self.is_bot = bot_url != ""

        self.requests_num = 0
        self.sessions_num = 0
        self.date = datetime.datetime.strptime("01/Jan/1980:00:00:00 +0000",
                                               TIME_FORMAT)

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
        dt = datetime.datetime.strptime(entry.time, TIME_FORMAT)

        if abs(dt - self.date) >= datetime.timedelta(minutes=SESSION_DELIM):
            self.sessions_num += 1
            rv = 1

        self.requests_num += 1
        self.date = dt
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


def anotate_bars(xs: List[float], ys: List[float], labels: List[int], rotation: int):
    for i, x in enumerate(xs):
        plt.annotate(str(labels[i]), (x, ys[i]),
                     rotation=rotation, horizontalalignment='center')


class Stat_struct:
    __slots__ = ("stats",
                 "day_req_distrib", "week_req_distrib", "month_req_distrib",
                 "day_sess_distrib", "week_sess_distrib", "month_sess_distrib",)

    def __init__(self):
        self.stats: Dict[str, Ip_stats] = {}
        self.day_req_distrib = [0 for _ in range(24)]
        self.day_sess_distrib = [0 for _ in range(24)]
        self.week_req_distrib = [0 for _ in range(7)]
        self.week_sess_distrib = [0 for _ in range(7)]
        self.month_req_distrib = Counter()
        self.month_sess_distrib = Counter()


class Log_stats:
    def __init__(self, input: Optional[TextIO] = None, err_mess=False):
        self.bots = Stat_struct()
        self.people = Stat_struct()
        self.err_mess = err_mess

        self.daily_data: Dict[str, Tuple[Set[str], int]] = {}
        self.year_stats: Dict[int, Tuple(Stat_struct, Stat_struct)] = {}
        self.current_year = None

        if input:
            self.make_stats(input)

    def make_stats(self, input: TextIO):
        if self.err_mess:
            timer = Ez_timer("Data parsing and proccessing")

        for line in input:
            # entry = Log_entry(line)
            entry = parse_log_entry(line)

            if len(entry) == 9:  # correct format of the log entry
                self._add_entry(entry)
            elif self.err_mess:
                print("log entry parsing failed:\n\t", entry, file=sys.stderr)

        if self.err_mess:
            timer.finish()

        self._switch_years(self.current_year)

    def _add_entry(self, entry: Log_entry):
        dt = datetime.datetime.strptime(entry.time, TIME_FORMAT)
        if self.current_year != dt.year:
            self._switch_years(dt.year)

        bot_url = entry.get_bot_url()

        if bot_url:
            stats = self.bots
            key = bot_url
        else:
            stats = self.people
            key = entry.ip_addr

        ip_stat = stats.stats.get(key)

        if ip_stat is None:
            ip_stat = Ip_stats(entry, bot_url)
        # 1 if new session was created, 0 otherwise
        new_sess = ip_stat.add_entry(entry)

        stats.stats[key] = ip_stat
        stats.day_req_distrib[ip_stat.date.hour] += 1
        stats.week_req_distrib[ip_stat.date.weekday()] += 1
        stats.month_req_distrib[(ip_stat.date.year, ip_stat.date.month)] += 1
        stats.day_sess_distrib[ip_stat.date.hour] += new_sess
        stats.week_sess_distrib[ip_stat.date.weekday()] += new_sess
        stats.month_sess_distrib[(
            ip_stat.date.year, ip_stat.date.month)] += new_sess

        # making daily_data for the picture
        date = ip_stat.date.date()
        ip_addreses, req_num = self.daily_data.get(date, (set(), 0))
        ip_addreses.add(ip_stat.ip_addr)
        self.daily_data[date] = (ip_addreses, req_num + 1)

    def _switch_years(self, year: int):
        if self.current_year is not None:
            self.year_stats[self.current_year] = (self.bots, self.people)

        self.current_year = year
        self.bots, self.people =\
            self.year_stats.get(year, (Stat_struct(), Stat_struct()))

    def print_stats(self,
                    output: TextIO,
                    geoloc_sample_size,
                    cctld_sample_size,
                    selected=True,
                    year=None):
        if year is not None:
            self._switch_years(year)

        html: Html_maker = Html_maker()
        if self.err_mess:
            timer = Ez_timer("making charts of bots and human users")

        self._print_bots(html, selected)
        self._print_users(html, selected)
        if self.err_mess:
            timer.finish()

        self._print_countries_stats(
            html, geoloc_sample_size, cctld_sample_size, selected)

        print(html.html(), file=output)

    def test_geolocation(self,
                         output: TextIO,
                         geoloc_sample_size=300,
                         cctld_sample_size=300,
                         selected=True,
                         repetitions: int = 1,
                         year: int = None):
        if year is not None:
            self._switch_years(year)

        html: Html_maker = Html_maker()
        self._test_geolocation(html,
                               geoloc_sample_size,
                               cctld_sample_size,
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
                                  True,
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

    def _print_most_frequent(self,
                             html: Html_maker,
                             req_sorted_stats: List[Ip_stats],
                             sess_sorted_stats: List[Ip_stats],
                             bots,
                             selected=""):

        html.append('<h3>Most frequent</h3>\n<label>Select:</label>')

        uniq_classes = html.print_sel_buttons(["session table", "requests table"],
                                              [[selected]] * 2)
        html.append("<div>")

        if bots:
            group_name = "bots"
            header = ["Rank", "Bot's url", "Host name",
                      "Requests count", "Sessions count"]

            def content_iter(data: List[Ip_stats], n: int):
                i = 0
                n = min(n, len(data))
                while i < n:
                    ip_stat = data[i]
                    ip_stat.update_host_name()
                    yield [f"{i + 1}",
                           ip_stat.bot_url,
                           ip_stat.host_name,
                           ip_stat.requests_num,
                           ip_stat.sessions_num
                           ]
                    i += 1
        else:
            group_name = "human users"
            header = ["Rank", "IP address", "Host name",
                      "Geolocation", "Requests count", "Sessions count"]

            def content_iter(data: List[Ip_stats], n: int):
                i = 0
                n = min(n, len(data))
                while i < n:
                    ip_stat = data[i]
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
        html.append(make_table(f"Most frequent {group_name} by number of sessions",
                               header,
                               content_iter(sess_sorted_stats, 20),
                               None,
                               ["selectable", selected, uniq_classes[0]]))

        html.append(make_table(f"Most frequent {group_name} by number of requests",
                               header,
                               content_iter(req_sorted_stats, 20),
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
                                       data.day_sess_distrib,
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

    def _test_geolocation(self,
                          html: Html_maker,
                          geoloc_sample_size: int,
                          tld_sample_size: int,
                          repetitions: int = 5,
                          selected: bool = False):

        # now olnly for human users
        data: List[Ip_stats] = list(self.people.stats.values())
        samples: List[List[Ip_stats]] = []
        sample_size = min(len(data),
                          max(geoloc_sample_size, tld_sample_size))

        for _ in range(repetitions):
            if len(data) > sample_size:
                samples.append(random.sample(data, sample_size))
            else:
                geoloc_sample_size = tld_sample_size = len(data)
                samples.append(data)

        # geolocation
        timer = Ez_timer("geolocations", verbose=self.err_mess)

        geoloc_stats = []
        for i, sample in enumerate(samples):
            timer2 = Ez_timer(f"geolocaion {i+1}", verbose=False)
            geostat = {}

            for ip_stat in sample[:geoloc_sample_size]:
                if not ip_stat.geolocation:
                    ip_stat.update_geolocation()
                value = geostat.get(ip_stat.geolocation, 0)
                geostat[ip_stat.geolocation] = value + (100 / sample_size)

            geoloc_stats.append(geostat)
            timer2.finish(self.err_mess)

        timer.finish(self.err_mess)

        # TLD stats
        timer = Ez_timer("TLD updates", verbose=self.err_mess)

        tld_stats = []
        for i, sample in enumerate(samples):
            timer2 = Ez_timer(f"TLD update {i+1}", verbose=False)
            tld_stat = {}

            for ip_stat in sample[:tld_sample_size]:
                if ip_stat.host_name == 'Unresolved':
                    ip_stat.update_host_name()
                tld = ip_stat.host_name.rsplit('.')[-1]
                value = tld_stat.get(tld, 0)
                tld_stat[tld] = value + (100 / sample_size)

            tld_stats.append(tld_stat)
            timer2.finish(self.err_mess)

        if self.err_mess:
            timer.finish()

        # Printing
        selected = "selected" if selected else ""

        html.append("<h3>Estimated locations</h3>\n<label>Select:</label>")
        button_names = [f"geoloc{i}" for i in range(1, repetitions + 1)]
        button_names.extend(f"tld {i}" for i in range(1, repetitions + 1))
        uniq_classes = html.print_sel_buttons(
            button_names,
            [["selectable", selected]]*(repetitions*2))

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

        # print tld
        html.append(f'<div class="flex-align-start">')
        for i in range(repetitions):
            html.append(
                f'<div class="selectable {selected} {uniq_classes[i+repetitions]}">')
            self.print_countries_bars(html,
                                      tld_stats[i],
                                      "Top level domains",
                                      max_size=20)
        html.append("</div>")

    def _print_countries_stats(self,
                               html: Html_maker,
                               geoloc_sample_size: int,
                               tld_sample_size: int,
                               selected: bool = False):
        # now olnly for human users
        data = self.people

        sample: List[Ip_stats] = list(data.stats.values())
        sample_size = min(len(sample),
                          max(geoloc_sample_size, tld_sample_size))
        if sample_size == 0:
            return

        if len(sample) > sample_size:
            sample = random.sample(sample, sample_size)
        else:
            geoloc_sample_size = tld_sample_size = len(sample)

        # geolocation
        if self.err_mess:
            timer = Ez_timer("geolocation")

        geoloc_stats = {}
        val_sum = 0

        for ip_stat in sample[:geoloc_sample_size]:
            if not ip_stat.geolocation:
                ip_stat.update_geolocation()

            value = geoloc_stats.get(ip_stat.geolocation, 0)
            value += ip_stat.requests_num  # weight the value by number of requests
            geoloc_stats[ip_stat.geolocation] = value
            val_sum += ip_stat.requests_num

        if self.err_mess:
            timer.finish()

        geoloc_stats = sorted(map(lambda x, s=val_sum: (x[0], 100 * x[1] / s),
                                  geoloc_stats.items()),
                              key=lambda x: x[1],
                              reverse=True)

        # TLD stats
        if self.err_mess:
            timer = Ez_timer("TLD update")

        tld_stats = {}
        val_sum = 0

        for ip_stat in sample[:tld_sample_size]:
            if ip_stat.host_name == 'Unresolved':
                ip_stat.update_host_name()
            tld = ip_stat.host_name.rsplit('.')[-1]
            value = tld_stats.get(tld, 0)
            value += ip_stat.requests_num
            tld_stats[tld] = value
            val_sum += ip_stat.requests_num

        if self.err_mess:
            timer.finish()
        
        tld_stats = sorted(map(lambda x, s=val_sum: (x[0], 100 * x[1] / s),
                               tld_stats.items()),
                           key=lambda x: x[1],
                           reverse=True)

        cctld_stats = {}
        val_sum = 0

        for ip_stat in sample[:tld_sample_size]:

            tld = ip_stat.host_name.rsplit('.')[-1]
            if tld in CCTLDS:
                country = CCTLDS[tld]
                value = cctld_stats.get(country, 0) 
                value += ip_stat.requests_num
                cctld_stats[country] = value
                val_sum += ip_stat.requests_num

        cctld_stats = sorted(map(lambda x, s=val_sum: (x[0], 100 * x[1] / s),
                                 cctld_stats.items()),
                    key=lambda x: x[1],
                    reverse=True)

        selected = "selected" if selected else ""

        html.append("<h3>Estimated locations</h3>\n<label>Select:</label>")
        uniq_classes = html.print_sel_buttons(
            ["Geoloc table", "Geoloc graph", " TLDs table", "TLDs", "ccTLD"],
            [[selected]]*5)

        if geoloc_sample_size > 0:
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

        if tld_sample_size > 0:
            # TLD table
            html.append(make_table("Most frequent top level domains",
                                   ["Rank", "TLD", "Percetns"],
                                   content_iter(tld_stats),
                                   classes=["selectable", selected, uniq_classes[2]]))

            # top level domains graphs
            html.append(
                f'<div class="selectable {selected} {uniq_classes[3]}">')
            self.print_countries_bars(html,
                                      tld_stats,
                                      "Top level domains",
                                      max_size=10)
            # ccTLD graph
            html.append(
                f'</div>\n<div class="selectable {selected} {uniq_classes[4]}">')
            self.print_countries_bars(html,
                                      cctld_stats,
                                      "Country code top level domains",
                                      left_margin=True,
                                      max_size=10)
            html.append('</div>')

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
