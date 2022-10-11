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
                  action="store", type="str", dest="o_file", default=None,
                  help="save the statisics as json, specify name of the file")
    parser.add_option("-l", "--load",
                  action="store", type="str", dest="i_file", default=None,
                  help="load the statisics from json, specify the name of the file")
                  


    options, _ = parser.parse_args()
    
    stats = Log_stats(err_mess=options.error)
    if options.i_file is not None:
        stats.load(options.i_file)
    else:
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
        if options.o_file is not None:
            stats.save(options.o_file)


def make_log_stats(log_stats: Log_stats, geoloc_ss: int, tld_ss: int, selected: bool):
    make_pictures(log_stats)

    for year in sorted(log_stats.year_stats.keys()):
        with open(f"{year}.html", "w") as file:
            log_stats.print_stats(file, geoloc_ss, tld_ss, selected, year)
    
    with open("logs_index.html", "w") as file:
        file.write("<h2>Overview</h2>\n")
        file.write("<h3>Requests</h3>\n")
        file.write("<img src='requests_overview.png'>\n")
        file.write("<h3>Unique IP addresses</h3>\n")
        file.write("<img src='unique_ip_overview.png'>\n")

        file.write("<h2>Statistics per year</h2>\n")
        file.write("<ul>\n")
        for year in log_stats.year_stats.keys():
            file.write(f"<li><a href='{year}.html'> year {year} </a></li>\n")
        file.write("</ul>\n")


if __name__ == '__main__':
    main()