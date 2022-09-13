from optparse import OptionParser
from log_stats import  Log_stats
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

    options, _ = parser.parse_args()
    
    stats = Log_stats(err_mess=options.error)
    stats.make_stats(sys.stdin)
    stats.print_stats(sys.stdout, options.geoloc_ss, options.tld_ss, selected=False)


if __name__ == '__main__':
    main()