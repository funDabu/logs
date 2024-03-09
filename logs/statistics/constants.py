"""
========== LOG FORMAT ==========
Edit
"""

LOG_DT_FORMAT = "%d/%b/%Y:%H:%M:%S %z"


"""
========== REGEX ==========
"""
SIMPLE_IPV4_REGEX = r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}"
BOT_URL_REGEX = r"(http\S+?)[);]"
BOT_USER_AGENT_REGEX = r"bot|Bot|crawl|Crawl|GoogleOther"

# Based on https://www.fi.muni.cz/tech/unix/external-network.html.cs
# 147.251.42–53.0/24, 147.251.58.0/24, 172.16.0.0/12
FI_MU_IPv4_REGEX = (
    r"147\.251\.(?:"
    + "|".join(str(n) for n in range(42, 54))
    + "|58"
    + r")\.[0-9]{1,3}$"
    + r"|^172\.(?:"
    + "|".join(str(n) for n in range(16, 32))
    + r")(?:\.[0-9]{1,3}){2}"
)

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

"""
========== Other ==========
"""

SESSION_DELIM = 1  # in minutes
GEOLOC_DB_PATH = "./_geoloc_db"  # path to geolocation database
