
from typing import Optional, Dict
from logs.statistics.ipstats import Ip_stats
from logs.statistics.helpers import IJSONSerialize

DISTRIB_ORDER = "day_req_distrib day_sess_distrib week_req_distrib week_sess_distrib month_req_distrib month_sess_distrib"
LOG_DELIM = "\t"


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
        self.month_req_distrib = [0] * 12
        self.month_sess_distrib = [0] * 12

    def _set_attr(self, name, data):
        if name == "stats":
            self.stats = {key: Ip_stats(None, json=stat) for key, stat in data.items()}
        else:
            setattr(self, name, data)

    def _get_attr(self, name: str):
        if name == "stats":
            return {key: stat.json() for key, stat in self.stats.items()}

        return getattr(self, name, None)

    def log_format_stats(
        self, format_str: Optional[str] = None, delim: Optional[str] = None
    ) -> str:
        """Returns representaion of the Ip_stats in self.stats as a log entries

        Parameters
        ----------
        format_str: str, optional
            default: ipstats.FORMAT_STR;
            format for a single log entry,
            string of Ip_stat attribute names separated by whitespace

        delim: str, optional
            default: '\t'; Ip_stat attribute delimiter in a log entry

        """
        return "\n".join(
            map(
                lambda ip_stat: ip_stat.log_format(format_str=format_str, delim=delim),
                self.stats.values(),
            )
        )

    def stats_from_log(
        self, log: str, format_str: Optional[str] = None, delim: Optional[str] = None
    ):
        """Sets `self.stats` according to a `log`

        Parameters
        ----------
        format_str: str, optional
            default: ipstats.FORMAT_STR;
            format for a single log entry,
            string of Ip_stat attribute names separated by whitespace

        delim: str, optional
            default: '\t'; Ip_stat attribute delimiter in a log entry

        """
        for line in log.split("\n"):
            ip_stat = Ip_stats("").from_log(line, format_str=format_str, delim=delim)
            self.stats[ip_stat.ip_addr] = ip_stat


    def log_format_distributions(
        self, delim: Optional[str] = None, format_str: Optional[str] = None
    ) -> str:
        """Returns representaion of "*_distrib" attributes of self as log entries

        Parameters
        ----------
        format_str: str, optional
            default: logstats.DISTRIB_ORDER;
            string of Ip_stat attribute names separated by whitespace
            definig the order of the self attributes in the output.


        delim: str, optional
            default: '\t'; distribution value delimiter in a log entry

        Returns
        -------
        str:
            a log of "*_distrib" attributes of self, each on new line
            in the order given by `format_str` parameter.
        """
        delim = LOG_DELIM if delim is None else delim
        format_str = DISTRIB_ORDER if format_str is None else format_str

        return "\n".join(
            delim.join(map(str, self._get_attr(attr))) for attr in format_str.split()
        )

    def distributions_from_log(
        self, log: str, delim: Optional[str] = None, format_str: Optional[str] = None
    ) -> str:
        """Returns representaion of "*_distrib" attributes of self as log entries

        Parameters
        ----------
        format_str: str, optional
            default: logstats.DISTRIB_ORDER;
            string of Ip_stat attribute names separated by whitespace
            definig the order of the self attributes in the output.


        delim: str, optional
            default: '\t'; distribution value delimiter in a log entry

        Returns
        -------
        str:
            a log of "*_distrib" attributes of self, each on new line
            in the order given by `format_str` parameter.

        """
        delim = LOG_DELIM if delim is None else delim
        format_str = DISTRIB_ORDER if format_str is None else format_str

        for name, log_entry in zip(format_str, log.split("\n")):
            self._set_attr(name, [int(val) for val in log_entry.split(delim)])
