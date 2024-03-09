import datetime
from typing import Dict, Tuple

from logs.statistics.constants import DATE_FORMAT, old_date
from logs.statistics.dailystat import Daily_stats
from logs.statistics.groupstats import Group_stats


class Log_stats:
    """Class for processing logs and storing statistical informations.
    Attributes
    ----------
    bots: Group_stats
        stores informations about bots for current year
    poeple: Group_stats
        stores informations about humna users for current year
    current_year: int, optional
    daily_data: Dict[datetime.date, Daily_stats]
        maps dates to a named tuples (<unique ips>, <number of requests>, <number of human sessions>)
        the tuple contains information related to the given date
        this information is used for making picture overview
    year_stats: Dict[int, Tuple(Group_stats, Group_stats)]
        maps years to tuples (<Group_stats for bots>, <Group_stats for people>)
    last_entry_ts: datetime.datetime
        timestamp of the latest log entry
    """

    def __init__(self):
        self.bots: Group_stats = Group_stats()
        self.people: Group_stats = Group_stats()
        self.daily_data: Dict[datetime.date, Daily_stats] = {}
        self.year_stats: Dict[int, Tuple[Group_stats, Group_stats]] = {}
        self.current_year: int = None
        self.last_entry_ts: datetime.datetime = old_date()

    def switch_year(self, year: int):
        """sets `self.current_year` to `year`
        and sets `self.bots`, `self.people` to `year` also"""
        if year not in self.year_stats:
            self.year_stats[year] = (Group_stats(), Group_stats())

        self.bots, self.people = self.year_stats.get(year)
        self.current_year = year

    def json(self):
        return {key: self._get_attr(key) for key in self.__dict__.keys()}

    def from_json(self, js):
        for key, data in js.items():
            self._set_attr(key, data)

    def _set_attr(self, name, data):
        if name == "bots":
            self.bots = Group_stats(data)
        elif name == "people":
            self.people = Group_stats(data)
        elif name == "daily_data":
            self.daily_data = {
                strp_date(d, DATE_FORMAT): Daily_stats(
                    strp_date(d, DATE_FORMAT), set(ips), r, s
                )
                for d, (ips, r, s) in data.items()
            }
        elif name == "year_stats":
            self.year_stats = {
                int(year): (Group_stats(b), Group_stats(p))
                for year, (b, p) in data.items()
            }
        else:
            setattr(self, name, data)

    def _get_attr(self, name: str):
        if name == "bots":
            return self.bots.json()
        if name == "people":
            return self.people.json()

        if name == "daily_data":
            return {
                dt.__format__(DATE_FORMAT): (
                    list(data.ips),
                    data.requests,
                    data.sessions,
                )
                for dt, data in self.daily_data.items()
            }

        if name == "year_stats":
            return {y: (b.json(), p.json()) for y, (b, p) in self.year_stats.items()}

        return getattr(self, name, None)


#################
### FUNCTIONS ###
#################


def strp_date(date: str, format: str) -> datetime.date:
    dt = datetime.datetime.strptime(date, format)
    return dt.date()

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
