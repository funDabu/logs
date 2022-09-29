from optparse import OptionParser
from log_stats import  Log_stats
from picture_overview import make_picture
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


    options, _ = parser.parse_args()
    
    stats = Log_stats(err_mess=options.error)
    stats.make_stats(sys.stdin)

    if options.test > 0:
        stats.test_geolocation(sys.stdout,
                               options.geoloc_ss,
                               options.tld_ss,
                               selected=False,
                               repetitions=options.test)
    elif options.year > 0:
        stats.print_stats(sys.stdout,
                          options.geoloc_ss,
                          options.tld_ss,
                          selected=False,
                          year=options.year)
    else:
        make_log_stats(stats, options.geoloc_ss, options.tld_ss, False)


def make_log_stats(log_stats: Log_stats, geoloc_ss: int, tld_ss: int, selected: bool):
    make_picture(log_stats, "overview.png")

    for year in log_stats.year_stats.keys():
        with open(f"{year}.html", "w") as file:
            log_stats.print_stats(file, geoloc_ss, tld_ss, selected, year)
    
    with open("logs_index.html", "w") as file:
        file.write("<img src='overview.png'>\n")
        file.write("<ul>\n")
        for year in log_stats.year_stats.keys():
            file.write(f"<li><a href='{year}.html'> year {year} </a></li>\n")
        file.write("</ul>\n")


if __name__ == '__main__':
    main()