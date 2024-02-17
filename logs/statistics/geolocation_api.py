import requests
import time

__geoloc_tokens = None  # www.geoplugin.net api oficial limit is 120 requsts/min
_TOKEN_MAX = 3
__last_geoloc_ts = time.time()  # time stamp of the last call to geolocation API
_SLEEP_TIME = 2  # seconds
_SESSION = requests.Session()  # for geolocation API


def geolocate(ip: str) -> str:
    """Calls geolocation API www.geoplugin.net and
    returns locations if given `ip`.

    Parameters
    ----------
    ip: str
        valid IPv4, if not valid, returns geolocation of the client

    Returns
    -------
    str
        geolocation of given `ip`,
        `"Unknown"` if location couldn't be found

    Note
    ----
    There is a limit for number of requests on the API,
    so the function will wait if the rate exceeds 3 calls per 2 seconds.
    """
    global __geoloc_tokens
    global __last_geoloc_ts
    time_from_last_call = __last_geoloc_ts - time.time()

    if __geoloc_tokens is None or time_from_last_call > _SLEEP_TIME:
        __geoloc_tokens = _TOKEN_MAX

    if not __geoloc_tokens:
        time.sleep(_SLEEP_TIME - time_from_last_call)
        __geoloc_tokens = _TOKEN_MAX

    __geoloc_tokens -= 1
    __last_geoloc_ts = time.time()

    return _geoplugin_call(ip)


def _geoplugin_call(ip: str) -> str:
    try:
        response = _SESSION.get(f"http://www.geoplugin.net/json.gp?ip={ip}").json()
        location = response["geoplugin_countryName"]
    except:  # noqa: E722
        location = "Unknown"

    return location
