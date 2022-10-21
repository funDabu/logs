from optparse import OptionParser
from log_stats import  Log_stats
from picture_overview import make_pictures
import sys


def main():
    parser = OptionParser()
    parser.add_option("-g", "--geolocation",
                  action="store", type="int", dest="geoloc_ss",
                  default=300, help="specify sample size for geolocation")
    parser.add_option("-t", "--TLD",
                  action="store", type="int", dest="tld_ss",
                  default=300, 
                  help="specify sample size for top level domain analysis")
    parser.add_option("-e", "--error",
                  action="store_true", dest="error", default=False,
                  help="print execution durations to stderr")
    parser.add_option("-T", "--test",
                  action="store", type="int", dest="test", default=0,
                  help="test geolocation, specify number of repetitions")
    parser.add_option("-y", "--year",
                  action="store", type="int", dest="year", default=0,
                  help="prints log statistics of given year to std.out")
    parser.add_option("-s", "--save",
                  action="store", type="str", dest="output_f", default=None,
                  help="save the statisics as json, specify name of the file")
    parser.add_option("-l", "--load",
                  action="store", type="str", dest="input_f", default=None,
                  help="load the statisics from json, specify the name of the file")
    parser.add_option("-H", "--histogram",
                  action="store_true", dest="hist", default=False,
                  help="makes html 'hist.html' with histograms")
    parser.add_option("-c", "--clean",
                  action="store_true", dest="clean", default=False,
                  help="when no --year is given and --clean is set, "
                       "then charts are not made. Good for use with --test or --histogram")
    parser.add_option("-C", "--config",
                  action="store", type="str", dest="config_f", default=None,
                  help="specify the name of configuration file, "
                       "ip addresses in config file will be calsified as bots")              

    options, _ = parser.parse_args()
    
    stats = Log_stats(err_msg=options.error, config_f=options.config_f)

    if options.input_f is not None:
        stats.load(options.input_f)
    else:
        stats.make_stats(sys.stdin)

    if options.test > 0:
        with open("_test.html", "w") as f:
            stats.test_geolocation(f,
                                   options.geoloc_ss,
                                   selected=False,
                                   repetitions=options.test)
    elif options.year > 0:
        stats.print_stats(sys.stdout,
                          options.geoloc_ss,
                          selected=False,
                          year=options.year)
    elif not options.clean:
        make_log_stats(stats, options, selected=False)

    if options.hist:
        stats.print_histogram("_hist.html")

    if options.output_f is not None:
        stats.save(options.output_f)


def make_log_stats(log_stats: Log_stats, options, selected: bool):
    make_pictures(log_stats)



    for year in sorted(log_stats.year_stats.keys()):
        with open(f"{year}.html", "w") as file:
            log_stats.print_stats(file, options.geoloc_ss, selected, year)
    
    with open("logs_index.html", "w") as file:
        file.write("<h2>Overview</h2>\n")
        file.write("<h3>Requests</h3>\n")
        file.write("<img src='requests_overview.png'>\n")
        file.write("<h3>Sessions</h3>\n")
        file.write("<img src='sessions_overview.png'>\n")
        file.write("<h3>Unique IP addresses</h3>\n")
        file.write("<img src='unique_ip_overview.png'>\n")

        file.write("<h2>Statistics per year</h2>\n")
        file.write("<ul>\n")
        for year in log_stats.year_stats.keys():
            file.write(f"<li><a href='{year}.html'> year {year} </a></li>\n")
        file.write("</ul>\n")


if __name__ == '__main__':
    main()