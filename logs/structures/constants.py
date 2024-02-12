"""
========== REGEX ==========
"""

# LOG_ENTRY_REGEX = r'([0-9.]+?) (.+?) (.+?) \[(.+?)\] "(.*?[^\\])" ([0-9]+?) ([0-9\-]+?) "(.*?)(?<!\\)" "(.*?)(?<!\\)"'
# ^ matches only numbers and dots in the first - 'ip adress' group
LOG_ENTRY_REGEX = r'(\S+) (.+?) (.+?) \[(.+?)\] "(.*?[^\\])" ([0-9]+?) ([0-9\-]+?) "(.*?)(?<!\\)" "(.*?)(?<!\\)"'
# ^ matches all nonwhitespace characters in the first - 'ip address' group
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
GEOLOC_DB_PATH = "./_geoloc_db"