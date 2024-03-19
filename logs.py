import sys
from optparse import OptionParser
from typing import List
from logs.helpers.simplelogger import SimpleLogger
from logs.statistics.dailystat import SimpleDailyStats

from logs.statistics.overviewpicture import make_pictures
from logs.statistics.print import make_histogram, print_stats, test_geolocation
from logs.statistics.geolocdb import GeolocDB
from logs.statistics.cache import (
    logstats_to_logcache,
    log_stats_from_cache,
    dailydata_to_logcache,
    simple_dailydata_from_logcache,
)
from logs.statistics.processing import (
    load_log_stats,
    make_stats,
    resolve_and_group_ips,
    save_log_stats,
    group_bots_on_url,
)


def main():
    options = parse_options()
    logger = SimpleLogger(sys.stderr) if options.error else None
    logger.addTask("Logs.py")

    log_stats = None
    cached_dailydata = []

    # load json or cache
    if options.json_in is not None:
        log_stats = load_log_stats(options.json_in, options.error, logger=logger)

    elif options.cache is not None:
        logger.addTask("loading cache")

        log_stats = log_stats_from_cache(base_path=options.cache)
        cached_dailydata = simple_dailydata_from_logcache(base_path=options.cache)

        logger.finishTask("loading cache")

    # parse and process log from input
    if options.input != '-':
        if options.input is None:
            log_stats = make_stats(
                sys.stdin, config_f=options.bot_config, logger=logger, cached_log_stats=log_stats
            )
        else:
            with open(options.input, "r") as input_f:
                log_stats = make_stats(
                    input_f, config_f=options.bot_config, logger=logger, cached_log_stats=log_stats
                )
    # fix nonvalid ips
    resolve_and_group_ips(log_stats, ip_map={}, logger=logger)

    # save to json or cache
    if options.json_out is not None:
        save_log_stats(log_stats, options.json_out, logger=logger)

    if options.cache is not None and options.input != '-':
        logger.addTask("saving cache")

        logstats_to_logcache(log_stats, base_path=options.cache)
        dailydata_to_logcache(
            log_stats.daily_data, cached_dailydata, base_path=options.cache
        )
        logger.finishTask("saving cache")
    
    if options.group_url:
        group_bots_on_url(log_stats=log_stats, logger=logger)

    # determine years
    years =  log_stats.year_stats.keys()
    if options.years is not None:
        years = set(years).intersection(options.years)
    years = sorted(years)

    geoloc_db = None if options.geoloc_db is None else GeolocDB(options.geoloc_db)
    selected = True

    # generate htmls for years
    logger.addTask("creating output html files")

    for year in years:
        with open(f"{year}.html", "w") as file:
            print_stats(
                log_stats,
                file,
                geoloc_sample_size=options.geoloc_sample,
                selected=selected,
                year=year,
                geoloc_db=geoloc_db,
                display_overview_imgs=True,
                logger=logger,
                log_name=options.name,
            )

    # Generate index html
    if options.index:
        index_years = years if options.just_years else log_stats.year_stats.keys()
        generate_index_html(options=options, years=index_years)
            
    logger.finishTask("creating output html files")

    # Generate overview pictures
    if options.pic_overview:
        logger.addTask("creating overview pictures")

        make_pictures(
            list(map(SimpleDailyStats.from_daily_stats, log_stats.daily_data.values())),
            cached_dailydata,
            years=years,
            name=options.name,
            purge_years=options.just_years
        )
        logger.finishTask("creating overview pictures")

    # generate histogram
    if options.hist:
        logger.addTask("creating histograms")
        make_histogram(log_stats, "hist.html", log_name=options.name)
        logger.finishTask("creating histograms")
    
    # test geolocation
    if options.test > 0:
        with open("_test.html", "w") as f:
            test_geolocation(
                log_stats,
                output=f,
                geoloc_sample_size=options.geoloc_sample,
                selected=selected,
                repetitions=options.test,
                geoloc_db=geoloc_db,
            )
    
    logger.finishTask("Logs.py")


OVERVIEW = """<h2>Overview</h2>
<h3>Requests</h3>
<img src='requests_overview.png'>
<h3>Sessions of human users</h3>
<img src='sessions_overview.png'>
<h3>Unique IP addresses</h3>
<img src='ips_overview.png'>
"""


def generate_index_html(options, years: List[int]):
    with open("logs_index.html", "w") as file:
        file.write("<html>\n<head>\n<style>")
        file.write(r"img { max-width: 100%; }")
        file.write("</style>\n</head>\n</body>\n")

        if options.name is not None:
            file.write(f"<h1>{options.name}</h1>\n")

        file.write(OVERVIEW)

        if options.hist:
            file.write("<h2>Histogram</h2>\n")
            file.write("<ul><li><a href='hist.html'> Histogram </a></li></ul>\n")

        file.write("<h2>Statistics per year</h2>\n")
        file.write("<ul>\n")

        for year in years:
            file.write(f"<li><a href='{year}.html'> year {year} </a></li>\n")
        file.write("</ul>\n")

        file.write("</body>\n</html>\n")


def parse_options():
    parser = OptionParser()
    
    parser.add_option(
        "-i",
        "--input",
        action="store",
        type="str",
        dest="input",
        default=None,
        help="Specify the path to input log file which will be procces; "
        "if not specified, standar input will be taken as input."
        "When equal to '-' no input is will be parsed, "
        "only data from cache of json might be used."
        "When used together with -l, --load or -c, --cache options, "
        "only entries older than loaded timestamp will be proccessed.",
    )
    parser.add_option(
        "-n",
        "--name",
        action="store",
        type="str",
        dest="name",
        default=None,
        help="Specify name of the porccessed log. "
        "Name will be diplayed output files",
    )
    parser.add_option(
        "-e",
        "--error",
        action="store_true",
        dest="error",
        default=False,
        help="log execution details to stderr",
    )
    parser.add_option(
        "-g",
        "--geolocation",
        action="store",
        type="int",
        dest="geoloc_sample",
        default=1000,
        help="sample size for geolocation",
    )
    parser.add_option(
        "-c",
        "--cache",
        action="store",
        type="str",
        dest="cache",
        default=None,
        help="specify the path to the directory where the cache direcory is located. "
        "Data from chache will be loaded, then merged together with proccessed data, "
        "and then saved to the chache."
        "If used together with -l, --load option, no cache will be loaded, but will be saved.",
    )
    parser.add_option(
        "-b",
        "--bot_config",
        action="store",
        type="str",
        dest="bot_config",
        default=None,
        help="Specify the path of the bot configuration file. "
        "That is plain text file, containing just an IPv4 on each line."
        "Ip addresses from the config file will be clasified as bots.",
    )
    parser.add_option(
        "-d",
        "--geoloc_database",
        action="store",
        type="str",
        dest="geoloc_db",
        default=None,
        help="Specify the path of geolocation database. "
        "This is SQLite database used for saving resolved geolocations",
    )
    parser.add_option(
        "-y",
        "--year",
        action="append",
        type="int",
        dest="years",
        default=None,
        help="Restrict generated output to given years. "
        "If not given, than all output for each present year will be generated. "
        "Use value '-' if you do not want to generate output for any year."
        "The restriction woun't apply to the general index html and the general overview pictures "
        "without the usage of -Y, --just_years option.",
    )
    parser.add_option(
        "-Y",
        "--just_years",
        action="store_true",
        dest="just_years",
        default=False,
        help="Restrict to given years also the content of "
        "the general index html and general overview pictures. "
        "To specify the years use -y, --year option.",
    )
    parser.add_option(
        "-H",
        "--no_histogram",
        action="store_false",
        dest="hist",
        default=True,
        help="Make no html file 'hist.html' with histograms. "
        "Note that histograms would ideally need some improvements2.",
    )
    parser.add_option(
        "-P",
        "--no_picture",
        action="store_false",
        dest="pic_overview",
        default=True,
        help="Don't make overview pictures",
    )
    parser.add_option(
        "-I",
        "--no_index",
        action="store_false",
        dest="index",
        default=True,
        help="Do not generate html index file",
    )
    parser.add_option(
        "-s",
        "--save",
        action="store",
        type="str",
        dest="json_out",
        default=None,
        help="Specify a name of a json file, "
        "which proccessed log statisics will be exported to",
    )
    parser.add_option(
        "-l",
        "--load",
        action="store",
        type="str",
        dest="json_in",
        default=None,
        help="Specify a json file, which proccessed statiscics will be loaded from. "
        "When used together with -c, --cache flag, no cache will be loaded",
    )
    parser.add_option(
        "-U",
        "--group_url",
        action="store_false",
        dest="group_url",
        default=True,
        help="Disable grouping bots on url",
    )
    parser.add_option(
        # TODO: meabe remove
        "-t",
        "--test",
        action="store",
        type="int",
        dest="test",
        default=0,
        help="Test geolocation, specify number of repetitions. ",
    )
    
    
    
    

    options, _ = parser.parse_args()
    return options


if __name__ == "__main__":
    main()
