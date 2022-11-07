"""
========== REGEX ==========
"""

LOG_ENTRY_REGEX = r'([0-9.]+?) (.+?) (.+?) \[(.+?)\] "(.*?[^\\])" ([0-9]+?) ([0-9\-]+?) "(.*?)(?<!\\)" "(.*?)(?<!\\)"'
TIME_REGEX = r'[0-9.]+? .+? .+? \[(.+?)\] '


"""
========== DATE and TIME ==========
"""
LOG_DT_FORMAT = "%d/%b/%Y:%H:%M:%S %z"
DT_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
DATE_FORMAT = "%Y-%m-%d"

MONTHS = ["Error", "Jan", "Feb", "Mar", "Apr", "May",
          "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = ["Mon", "Tue", "Wed", "Thr", "Fri", "Sat", "Sun"]