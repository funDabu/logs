import re

"""
========== REGEX ==========
"""

SIMPLE_IPV4_REGEX = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
RE_PATTERN_SIMPLE_IPV4 = re.compile(SIMPLE_IPV4_REGEX)

BOT_URL_REGEX = r"(http\S+?)[);]"
RE_PATTERN_BOT_URL = re.compile(BOT_URL_REGEX)

BOT_USER_AGENT_REGEX = r"bot|Bot|crawl|Crawl|GoogleOther"
RE_PATTERN_BOT_USER_AGENT = re.compile(BOT_USER_AGENT_REGEX)

# Based on https://www.fi.muni.cz/tech/unix/external-network.html.cs
# 147.251.42–53.0/24, 147.251.58.0/24, 172.16.0.0/12
FI_MU_IPv4_REGEX = \
    r"^147\.251\.(?:" \
    + '|'.join(str(n) for n in range(42,54)) \
    + "|58" \
    + r")\.[0-9]{1,3}$"  \
    + r"|^172\.(?:" \
    + '|'.join(str(n) for n in range(16,32)) \
    + r")(?:\.[0-9]{1,3}){2}$"

RE_PATTERN_FI_MU_IPv4 = re.compile(FI_MU_IPv4_REGEX)

"""
========== Other ==========
"""

SESSION_DELIM = 1  # in minutes
