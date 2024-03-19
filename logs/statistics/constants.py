"""
========== LOG FORMAT ==========
Edit
"""

import datetime


LOG_DT_FORMAT = "%d/%b/%Y:%H:%M:%S %z"


"""
========== REGEX ==========
"""
SIMPLE_IPV4_REGEX = r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}"
BOT_URL_REGEX = r"(http\S+?)[);]"
BOT_USER_AGENT_REGEX = r"bot|Bot|crawl|Crawl|GoogleOther|scan"

"""
========== DATE and TIME ==========
"""
DATE_FORMAT = "%Y-%m-%d"

MONTHS = [
    "Error",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
DAYS = ["Mon", "Tue", "Wed", "Thr", "Fri", "Sat", "Sun"]

def old_date() -> datetime.datetime:
    """Return datetime.datetime object of 01/Jan/1980"""
    return datetime.datetime.strptime(
        "01/Jan/1980:00:00:00 +0000", "%d/%b/%Y:%H:%M:%S %z"
    )

"""
========== Other ==========
"""

SESSION_DELIM = 1  # in minutes
GEOLOC_DB_PATH = "./_geoloc_db"  # path to geolocation database
