import datetime
import os
from typing import Dict, List, Optional

from logs.statistics.constants import LOG_DT_FORMAT
from logs.statistics.dailystat import (
    Daily_stats,
    Simple_daily_stats,
    daily_stats_to_simple,
    log_format_simple_daily_stats,
    simple_daily_stats_from_log,
)
from logs.statistics.logstats import Log_stats

LOG_CACHE = "logcache"


def logstats_to_logcache(
    log_stats: Log_stats,
    base_path: str = ".",
    bot_stats_file: str = "bot_stats_file",
    human_stats_file: str = "human_stats_file",
    bot_distrib_file: str = "bot_distrib_file",
    human_distrib_file: str = "human_distrib_file",
    last_ts_file: str = "last_ts_file",
):
    """Writes `log_stats` into log cache

    Note
    ----
    Does not write `log_stats.daily_data` into the cache

    See also
    --------
    dailydata_to_logcache
    """
    cache_path = os.path.join(base_path, LOG_CACHE)
    os.makedirs(cache_path, exist_ok=True)

    for year, (bots, humans) in log_stats.year_stats.items():
        with open(os.path.join(cache_path, f"{year}-{bot_stats_file}"), "w") as f:
            f.write(bots.log_format_stats())

        with open(os.path.join(cache_path, f"{year}-{human_stats_file}"), "w") as f:
            f.write(humans.log_format_stats())

        with open(os.path.join(cache_path, f"{year}-{bot_distrib_file}"), "w") as f:
            f.write(bots.log_format_distributions())

        with open(os.path.join(cache_path, f"{year}-{human_distrib_file}"), "w") as f:
            f.write(humans.log_format_distributions())

    with open(os.path.join(cache_path, last_ts_file), "w") as f:
        f.write(log_stats.last_entry_ts.__format__(LOG_DT_FORMAT))


def dailydata_to_logcache(
    daily_data: Dict[datetime.date, Daily_stats],
    cached_daily_data: List[Simple_daily_stats] = [],
    base_path: str = ".",
    daily_data_file: str = "daily_data_file",
):
    """Writes `daily_data` sorted by date to log cache,
    if `cached_daily_data` is given then
    `daily_data` follows after the `cached_daily_data` in the log
    """
    cache_path = os.path.join(base_path, LOG_CACHE)
    os.makedirs(cache_path, exist_ok=True)

    sorted_daily_data = sorted(
        map(daily_stats_to_simple, daily_data.values()), key=lambda ds: ds.date
    )
    merged = merge_simple_dailydata(older=cached_daily_data, newer=sorted_daily_data)

    with open(os.path.join(cache_path, daily_data_file), "w") as f:
        f.writelines(log_format_simple_daily_stats(ds) + "\n" for ds in merged)


def log_stats_from_cache(
    log_stats: Log_stats,
    base_path: str = ".",
    bot_stats_file: str = "bot_stats_file",
    human_stats_file: str = "human_stats_file",
    bot_distrib_file: str = "bot_distrib_file",
    human_distrib_file: str = "human_distrib_file",
    last_ts_file: str = "last_ts_file",
) -> Optional[Log_stats]:
    """Loads into `logs_stats` data from log cache

    Returns
    -------
    Log_stats
        with loaded data from chache
    None
        if cache directory does not exist

    Note
    ----
    does not load anything to `log_stats.daily_data`

    See also
    --------
    simple_dailydata_from_logcache
    """

    cache_path = os.path.join(base_path, LOG_CACHE)

    if not os.path.isdir(cache_path):
        return

    log_stats = Log_stats()

    for file in os.listdir(cache_path):
        if file == last_ts_file:
            with open(os.path.join(cache_path, last_ts_file), "r") as f:
                log_stats.last_entry_ts = datetime.datetime.strptime(
                    f.read(), LOG_DT_FORMAT
                )

        elif bot_stats_file in file:
            year = int(file.split("-")[0])
            log_stats.switch_year(year)

            with open(os.path.join(cache_path, file), "r") as f:
                log_stats.bots.stats_from_log(f.read())

        elif human_stats_file in file:
            year = int(file.split("-")[0])
            log_stats.switch_year(year)

            with open(os.path.join(cache_path, file), "r") as f:
                log_stats.people.stats_from_log(f.read())

        elif bot_distrib_file in file:
            year = int(file.split("-")[0])
            log_stats.switch_year(year)

            with open(os.path.join(cache_path, file), "r") as f:
                log_stats.bots.distributions_from_log(f.read())

        elif human_distrib_file in file:
            year = int(file.split("-")[0])
            log_stats.switch_year(year)

            with open(os.path.join(cache_path, file), "r") as f:
                log_stats.people.distributions_from_log(f.read())

    return log_stats


def simple_dailydata_from_logcache(
    base_path: str = ".",
    daily_data_file: str = "daily_data_file",
) -> Optional[List[Simple_daily_stats]]:
    """Returns
    -------
    List[Simple_daily_stats]
        list of loaded simple_daily_stats from thr chache
    None
        if cache directory does not exist
    """

    cache_path = os.path.join(base_path, LOG_CACHE)

    if not os.path.isdir(cache_path):
        return

    with open(os.path.join(cache_path, daily_data_file), "r") as f:
        simple_daily_data = list(map(simple_daily_stats_from_log, f.readlines()))

    return simple_daily_data

def merge_simple_dailydata(older: List[Simple_daily_stats], newer:List[Simple_daily_stats]) -> List[Simple_daily_stats]:
    """Merge two lists if Simple_daily_stats in one. Raises ValueError

    Used for merging cached daily_data with newly parsed daily_data from log_stats.
    
    Parameters
    ----------
    older: List[Simple_daily_stats]
        list of Simple_daily_stats sorted by date
    newer: List[Simple_daily_stats]
        list of Simple_daily_stats sorted by date,
        last simple_daily_stat from `older` cannot have more recent date
        than the first simple_daily_stat from `newer`.
    
    Returns
    -------
    List[Simple_daily_stats]
        Concatenation of `older` and `newer`,
        if the date of last simple_daily_stat from `older` 
        is equal to the date of the first simple_daily_stat from `newer`,
        date these two simple_daily_stat are merget in the result,
        by summing their values.
    
    """
    if not newer:
        return older
    if not older:
        return newer
    
    if older[-1].date > newer[0].date:
        raise ValueError(
            "Error in dailydata_to_logcache: last daily_stats in older "
            "cannot be older than firt daily_stat in daily_data"
        )

    if older[-1].date == newer[0].date:
        summed_stat = Simple_daily_stats(
            older[-1].date,
            older[-1].ips + newer[0].ips,
            older[-1].requests + newer[0].requests,
            older[-1].sessions + newer[0].sessions,
        )
        return older[:-1] + [summed_stat] + newer[1:]

    return older + newer
