import datetime
import re
import socket
from typing import Dict, Optional, Tuple

import logs.statistics.geolocapi as geolocapi
from logs.statistics.constants import SIMPLE_IPV4_REGEX, old_date
from logs.statistics.geolocdb import GeolocDB
from logs.helpers.ijsonserialize import IJsonSerialize
UNRESLOVED = "Unresolved"
DT_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
FORMAT_STR = (
    "ip_addr host_name geolocation bot_url is_bot requests_num sessions_num datetime valid_ip"
)
LOG_DELIM = '\t'
RE_PATTERN_SIMPLE_IPV4 = re.compile(SIMPLE_IPV4_REGEX)


class IpStats(IJsonSerialize):
    """Data structure to store informations about requests
    from a single IP address.
    Implements IJSONSerialize

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
        default: 01/Jan/1980:00:00:00 +0000
    valid_ip: Optional[bool]
        `None` if not yet validated, `True` if `ip_addr` is valid IPv4, 
        `False` if valid IP could not be resovled.

    """

    __slots__ = (
        "ip_addr",
        "host_name",
        "geolocation",
        "bot_url",
        "is_bot",
        "requests_num",
        "sessions_num",
        "datetime",
        "valid_ip",
    )

    def __init__(
        self,
        ip_addr: str,
        is_bot: Optional[bool] = None,
        bot_url=UNRESLOVED,
        json: Optional[str] = None,
    ) -> None:
        if json is not None:
            self.from_json(json)
            return

        self.ip_addr = ip_addr
        self.host_name = UNRESLOVED
        self.geolocation = UNRESLOVED
        self.requests_num = 0
        self.sessions_num = 0
        self.is_bot = is_bot
        self.bot_url = bot_url
        self.datetime = old_date()
        self.valid_ip = None

    def update_host_name(self) -> None:
        """Resolves `self.ip_addr` to host name and sets `self.host_name`
        approprietaly or to `"Unknown"` if resolution fails"""
        try:
            self.host_name = socket.gethostbyaddr(self.ip_addr)[0]
        except:  # noqa: E722
            self.host_name = "Unknown"

    def get_short_host_name(self, precision: int = 3) -> str:
        """Returns `self.host_name` shortend to last (top) `n` domains"""
        hostname = self.host_name
        hostname = hostname.rsplit(".")

        if len(hostname) > precision:
            hostname = hostname[-precision:]

        hostname = ".".join(hostname)
        return hostname

    def ensure_valid_ip_address(self, ip_map: Optional[Dict[str, str]] = None) -> bool:
        """Does a simple validation of `self.ip_addr` and sets `self.valid_ip` accordingly.
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
            self.valid_ip = True
            return True

        if ip_map is not None:
            ip = ip_map.get(self.ip_addr)

            if ip is not None:
                self.host_name = self.ip_addr
                self.ip_addr = ip
                self.valid_ip = True
                return True

        valid, ip = host_to_ip(self.ip_addr)

        if ip_map is not None:
            ip_map[self.ip_addr] = ip

        if valid:
            self.host_name = self.ip_addr
            self.ip_addr = ip
            self.valid_ip = True
        else:
            self.valid_ip = False

        return valid

    def update_geolocation(self, database: Optional[GeolocDB] = None):
        """Updates `self.geolocation`.
        First tries to find the location in `database` if was given,
        then calls `self.geolocate_with_api()`.
        Saves found location to `database
        `"""
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
        """Calls geolocation API and sets `self.geolocation` approprietaly,
        sets it to `"Unknown"` if location couldn't be found"""
        if not self.ensure_valid_ip_address():
            self.geolocation = "Unknown"
            return

        self.geolocation = geolocapi.geolocate(self.ip_addr)

    def _get_attr(self, name: str):
        if name == "datetime":
            return self.datetime.__format__(DT_FORMAT)
        return getattr(self, name, None)

    def _set_attr(self, name: str, data):
        if name == "datetime":
            self.datetime = datetime.datetime.strptime(data, DT_FORMAT)
        else:
            setattr(self, name, data)

    def log_format(
        self, format_str: Optional[str] = None, delim: Optional[str] = "\t"
    ) -> str:
        """Returns representaion of the object as a log entry

        Parameters
        ----------
        format_str: str, optional
            default: ipstats.FORMAT_STR;
            string of attributes name separated by whitespace

        delim: str, optional
            default: '\t'; attributes delimiter in the log entry

        """
        format_str = FORMAT_STR if format_str is None else format_str
        delim = LOG_DELIM if delim is None else delim

        return delim.join(str(self._get_attr(attr)) for attr in format_str.split())
    
    def from_log(self, log_entry: str, format_str: Optional[str] = None, delim: Optional[str] = None) -> "IpStats":
        """Sets attributes of the object according to  `log_entry`

        Parameters
        ----------
        format_str: str, optional
            default: ipstats.FORMAT_STR;
            string of attributes name separated by whitespace

        delim: str, optional
            default: ipstats.LOG_DELIM; attributes delimiter in the log entry
        """

        format_str = FORMAT_STR if format_str is None else format_str
        delim = LOG_DELIM if delim is None else delim

        for name, value in zip(format_str.split(), log_entry.split(delim)):
            if name == "requests_num" or name == "sessions_num":
                value = int(value)
            elif name == "is_bot":
                value = value == "True"
            elif name == "valid_ip":
                if value == "True":
                    value = True
                elif value == "False":
                    value = False
                else:
                    value = None

            self._set_attr(name, value)
        
        return self



"""
========== FUNCTIONS ==========
"""


def simple_ipv4_check(ip: str) -> bool:
    """Non-exhaustivly tests if `ip` is already a valid IPv4

    Returns
    -------
    bool
        - `True` if `ip` is valid IPv4
        - `False` otherwise
    """
    return RE_PATTERN_SIMPLE_IPV4.fullmatch(ip) is not None


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
    except:  # noqa: E722
        return (False, host)
