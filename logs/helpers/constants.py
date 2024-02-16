# Contains constants common for logs package


"""
========== REGEX ==========
"""

# LOG_ENTRY_REGEX = r'([0-9.]+?) (.+?) (.+?) \[(.+?)\] "(.*?[^\\])" ([0-9]+?) ([0-9\-]+?) "(.*?)(?<!\\)" "(.*?)(?<!\\)"'
# matches only numbers and dots in the first - 'Host' group - eg. excepts only IPv4 as a host
LOG_ENTRY_REGEX = r'(\S+) (.+?) (.+?) \[(.+?)\] "(.*?[^\\])" ([0-9]+?) ([0-9\-]+?) "(.*?)(?<!\\)" "(.*?)(?<!\\)"'
# matches all nonwhitespace characters in the first - 'Host' group - e.g allows for both IP address and hostname as a host
TIME_REGEX = r'\S+ .+? .+? \[(.+?)\] '



"""
========== DATE and TIME ==========
"""
LOG_DT_FORMAT = "%d/%b/%Y:%H:%M:%S %z"
DT_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
DATE_FORMAT = "%Y-%m-%d"

MONTHS = ["Error", "Jan", "Feb", "Mar", "Apr", "May",
          "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = ["Mon", "Tue", "Wed", "Thr", "Fri", "Sat", "Sun"]

"""
========== PATHS ==========
"""
GEOLOC_DB_PATH = "./_geoloc_db" # TODO is it used??