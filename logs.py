import sys
from optparse import OptionParser
from typing import List, Optional
from logs.statistics.dailystat import Simple_daily_stats, daily_stats_to_simple

from logs.statistics.picture_overview import make_pictures
from logs.statistics.print import make_histogram, print_stats, test_geolocation
from logs.statistics.geoloc_db import GeolocDB
from logs.statistics.cache import (
    logstats_to_logcache,
    log_stats_from_cache,
    dailydata_to_logcache,
    simple_dailydata_from_logcache,
)
from logs.statistics.processing import (
    Log_stats,
    load_log_stats,
    make_stats,
    resolve_and_group_ips,
    save_log_stats,
)

OVERVIEW = """<h2>Overview</h2>
<h3>Requests</h3>
<img src='requests_overview.png'>
<h3>Sessions of human users</h3>
<img src='sessions_overview.png'>
<h3>Unique IP addresses</h3>
<img src='ips_overview.png'>
"""


def parse_options():
    parser = OptionParser()
    parser.add_option(
        "-g",
        "--geolocation",
        action="store",
        type="int",
        dest="geoloc_ss",
        default=1000,
        help="specify sample size for geolocation",
    )
    parser.add_option(
        "-e",
        "--error",
        action="store_true",
        dest="error",
        default=False,
        help="print execution durations to stderr",
    )
    parser.add_option(
        "-T",
        "--test",
        action="store",
        type="int",
        dest="test",
        default=0,
        help="test geolocation, specify number of repetitions",
    )
    parser.add_option(
        "-y",
        "--year",
        action="store",
        type="int",
        dest="year",
        default=0,
        help="prints log statistics of given year to std.out",
    )
    parser.add_option(
        "-s",
        "--save",
        action="store",
        type="str",
        dest="output_f",
        default=None,
        help="export the statisics as json, specify name of the file",
    )
    parser.add_option(
        "-n",
        "--name",
        action="store",
        type="str",
        dest="name",
        default=None,
        help="specify name of the log. Name will be heading 1"
        " in logs_index.html file",
    )
    parser.add_option(
        "-l",
        "--load",
        action="store",
        type="str",
        dest="load_file",
        default=None,
        help="load the statisics from json, specify the name of the file",
    )
    parser.add_option(
        "-H",
        "--histogram",
        action="store_true",
        dest="hist",
        default=False,
        help="makes html file 'hist.html' with histograms",
    )
    parser.add_option(
        "-p",
        "--pictureoverview",
        action="store_true",
        dest="pic_overview",
        default=False,
        help="makes picture overview",
    )
    parser.add_option(
        "-L",
        "--clean",
        action="store_true",
        dest="clean",
        default=False,
        help="when no --year is given and --clean is set, "
        "then no charts are made. Good for use with --test,  "
        "--histogram or --pictureoverview",
    )
    parser.add_option(
        "-i",
        "--ignore",
        action="store_true",
        dest="ignore",
        default=False,
        help="ignore data from std input, "
        "has to be used together with --load option",
    )
    parser.add_option(
        "-C",
        "--config",
        action="store",
        type="str",
        dest="config_f",
        default=None,
        help="specify the path of configuration file, "
        "ip addresses in config file will be clasified as bots",
    )
    parser.add_option(
        "-d",
        "--geoloc-database",
        action="store",
        type="str",
        dest="geoloc_db",
        default=None,
        help="specify the path of geolocation database",
    )
    parser.add_option(
        "-f",
        "--input_log",
        action="store",
        type="str",
        dest="input",
        default=None,
        help="specify the path of input log file",
    )
    parser.add_option(
        "-c",
        "--cache",
        action="store",
        type="str",
        dest="cache",
        default=None,
        help="specify the path to the directory where the cache direcory is located. "
        "If used together with -l, --load option, than the cache is only written to, but not read from.",
    )

    options, _ = parser.parse_args()
    return options


def main():
    options = parse_options()
    log_stats = None
    cached_dailydata = []

    if options.load_file is not None:
        log_stats = load_log_stats(options.load_file, options.error)
    elif options.cache is not None:
        log_stats = log_stats_from_cache(log_stats, base_path=options.cache)
        cached_dailydata = simple_dailydata_from_logcache(base_path=options.cache)

    if options.load_file is None or not options.ignore:
        if options.input is not None:
            with open(options.input, "r") as input_f:
                log_stats = make_stats(
                    input_f, config_f=options.config_f, err_msg=options.error, cached_log_stats=log_stats
                )
        log_stats = make_stats(
            sys.stdin, config_f=options.config_f, err_msg=options.error, cached_log_stats=log_stats
        )

    resolve_and_group_ips(log_stats, ip_map={}, err_msg=options.error)

    if options.output_f is not None:
        save_log_stats(log_stats, options.output_f, err_msg=options.error)

    if options.cache is not None:
        logstats_to_logcache(log_stats, base_path=options.cache)
        dailydata_to_logcache(
            log_stats.daily_data, cached_dailydata, base_path=options.cache
        )

    geoloc_db = None if options.geoloc_db is None else GeolocDB(options.geoloc_db)

    if options.year > 0:
        print_stats(
            log_stats,
            output=sys.stdout,
            geoloc_sample_size=options.geoloc_ss,
            selected=False,
            year=options.year,
            geoloc_db=geoloc_db,
            display_overview_imgs=True,
        )

    elif not options.clean:
        make_log_stats(
            log_stats,
            options=options,
            selected=False,
            cached_dailydata=cached_dailydata,
            geoloc_db=geoloc_db,
        )

    if options.test > 0:
        with open("_test.html", "w") as f:
            test_geolocation(
                log_stats,
                output=f,
                geoloc_sample_size=options.geoloc_ss,
                selected=False,
                repetitions=options.test,
                geoloc_db=geoloc_db,
            )
    if options.pic_overview:
        years = log_stats.year_stats.keys()
        make_pictures(
            list(map(daily_stats_to_simple, log_stats.daily_data.values())),
            cached_dailydata,
            separate_years=years,
        )

    if options.hist:
        make_histogram(log_stats, "_hist.html")


def make_log_stats(
    log_stats: Log_stats,
    options,
    selected: bool,
    cached_dailydata: List[Simple_daily_stats] = [],
    geoloc_db: Optional[GeolocDB] = None,
):
    make_pictures(
        list(map(daily_stats_to_simple, log_stats.daily_data.values())),
        cached_dailydata,
    )

    for year in sorted(log_stats.year_stats.keys()):
        with open(f"{year}.html", "w") as file:
            print_stats(
                log_stats,
                file,
                geoloc_sample_size=options.geoloc_ss,
                selected=selected,
                year=year,
                geoloc_db=geoloc_db,
                display_overview_imgs=True,
                err_msg=options.error,
            )

    with open("logs_index.html", "w") as file:
        file.write("<html>\n<head>\n<style>")
        file.write(r"img { max-width: 100%; }")
        file.write("</style>\n</head>\n</body>\n")

        if options.name is not None:
            file.write(f"<h1>{options.name}</h1>\n")
        if options.pic_overview:
            file.write(OVERVIEW)
        if options.hist:
            file.write("<h2>Histogram</h2>\n")
            file.write("<ul><li><a href='_hist.html'> Histogram </a></li></ul>\n")

        file.write("<h2>Statistics per year</h2>\n")
        file.write("<ul>\n")
        for year in log_stats.year_stats.keys():
            file.write(f"<li><a href='{year}.html'> year {year} </a></li>\n")
        file.write("</ul>\n")

        file.write("</body>\n</html>\n")


if __name__ == "__main__":
    main()
