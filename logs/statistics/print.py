import io
import os
import random
import re
from typing import List, Optional, TextIO, Tuple

import matplotlib.pyplot as plt

from logs.htmlmaker.html_maker import Html_maker, make_table
from logs.statistics.constants import DAYS, MONTHS, FI_MU_IPv4_REGEX
from logs.statistics.geoloc_db import GeolocDB
from logs.statistics.helpers import Ez_timer
from logs.statistics.processing import Ip_stats, Log_stats

RE_PATTERN_FI_MU_IPv4 = re.compile(FI_MU_IPv4_REGEX)


def print_stats(
    log_stats: Log_stats,
    output: TextIO,
    geoloc_sample_size: int,
    selected: bool = True,
    year: int = None,
    geoloc_db: Optional[str] = None,
    display_overview_imgs: bool = False,
    err_msg: bool = False,
) -> None:
    """Transforms data for given year from `log_stats`
    into html files and writes it into `output`

    Parameters
    ----------
    log_stats : Log_stats
        input data for this function,
        contains data from parsed log
        which will be transformed into html file
    output: TextIO
        the IO to write the html file into
    geoloc_sample_size: int
        the size of sample for geolocation.
        Geolocation can cost a lot of time
    year: int, optional
        default: `log_stats.current_year`;
        the year for which the output html will be created
    geoloc_db: str, optional
        path to SQLite database of IP geolocations,
        if database doesent exist in the path, it will be created.
        If not given, then no database will be used
    selected: bool, optional
        default: `True`;
        determines the selection state for selection buttons in output html
    display_overview_imgs: bool
        default: `False`;
        if 'True', then overview pictures for given `year` will be created
        and linked in the beginnig of the output html
    err_msg: bool, optional
        default: `False`; if `True` then the duration of this function
        will be printed to std.err
    """
    html: Html_maker = Html_maker()

    if year is not None:
        log_stats.switch_year(year)

    html.append(f"<h1>Year {log_stats.current_year}</h1>")

    if err_msg:
        timer = Ez_timer("making charts of bots and human users")

    if display_overview_imgs:
        display_overview_images(log_stats, html)

    print_bots(log_stats, html, selected, geoloc_db)
    print_users(log_stats, html, selected, geoloc_db)

    if err_msg:
        timer.finish()

    print_countries_stats(log_stats, html, geoloc_sample_size, selected, geoloc_db)

    print(html.html(), file=output)


def display_overview_images(log_stats: Log_stats, html: Html_maker):
    """Appends links for picture overviews for `log_stats.current_year`
    to `html`
    """
    overview = """<h2>Picture overview</h2>
<h3>Requests</h3>
<img src='requests_{0}_overview.png'>
<h3>Sessions of human users</h3>
<img src='sessions_{0}_overview.png'>
<h3>Unique IP addresses</h3>
<img src='ips_{0}_overview.png'>
"""
    html.append(overview.format(log_stats.current_year))


def test_geolocation(
    log_stats: Log_stats,
    output: TextIO,
    geoloc_sample_size=300,
    selected=True,
    repetitions: int = 1,
    year: int = None,
    geoloc_db: Optional[GeolocDB] = None,
):
    if year is not None:
        log_stats.switch_year(year)

    html: Html_maker = Html_maker()
    _test_geolocation(
        log_stats,
        html,
        geoloc_sample_size,
        selected=selected,
        repetitions=repetitions,
        geoloc_db=geoloc_db,
    )

    print(html.html(), file=output)


def print_bots(
    log_stats, html: Html_maker, selected=True, geoloc_db: Optional[GeolocDB] = None
) -> None:
    """Transforms data about bot from `logs_stats` to html
    and appends it to `html`

    The html will contain:
       - overview table
       - most frequent table
       - day, week, month distributions
    """
    html.append("<h2>Bots</h2>")

    req_sorted_stats, sess_sorted_stats = sort_stats(log_stats, True)

    print_overview(html, "Bots count", req_sorted_stats)
    if len(req_sorted_stats) == 0:
        return

    selected = "selected" if selected else ""

    print_most_frequent(
        html, req_sorted_stats, sess_sorted_stats, True, selected, geoloc_db=geoloc_db
    )

    print_day_distribution(log_stats, html, True, selected)
    print_week_distribution(log_stats, html, True, selected)
    print_month_distributions(log_stats, html, True, selected)


def print_users(
    log_stats: Log_stats,
    html: Html_maker,
    selected=True,
    geoloc_db: Optional[GeolocDB] = None,
):
    """Transforms data about human users from `logs_stats` to html
    and appends it to `html`

    The html will contain:
       - overview table
       - most frequent table
       - day, week, month distributions
    """
    html.append("<h2>Human users</h2>")
    req_sorted_stats, sess_sorted_stats = sort_stats(log_stats, False)

    print_overview(html, "Different IP addresses count", req_sorted_stats)
    if len(req_sorted_stats) == 0:
        return

    selected = "selected" if selected else ""

    print_most_frequent(
        html, req_sorted_stats, sess_sorted_stats, False, selected, geoloc_db=geoloc_db
    )
    print_day_distribution(log_stats, html, False, selected)
    print_week_distribution(log_stats, html, False, selected)
    print_month_distributions(log_stats, html, False, selected)


def print_overview(
    html: Html_maker, header_str: str, req_sorted_stats: List[Ip_stats]
) -> None:
    """Creates overivew html table from`req_sorted_stats` and appends it to `html`

    The overview will contain onw row and following columns:
        - `header_str`: number of Ip_stats
        - Total session count: sum of all the session counts in `req_sorted_stats`
        - FI MU sessions: sum of all the session counts in `req_sorted_stats` for
          IP addresses from FI MU
        - External sessions: Total session count - FI MU sessions
    """
    total_session_num = sum(map(lambda ip_stat: ip_stat.sessions_num, req_sorted_stats))
    fi_mu_session_num = 0

    for stat in req_sorted_stats:
        if RE_PATTERN_FI_MU_IPv4.search(stat.ip_addr) is not None:
            fi_mu_session_num += stat.sessions_num

    html.append(
        make_table(
            "Overview",
            [header_str, "Total sessions count", "FI MU sessions", "External sessions"],
            [
                [
                    str(len(req_sorted_stats)),
                    str(total_session_num),
                    str(fi_mu_session_num),
                    str(total_session_num - fi_mu_session_num),
                ]
            ],
        )
    )


def sort_stats(
    log_stats: Log_stats, bot: bool
) -> Tuple[List[Ip_stats], List[Ip_stats]]:
    """Sorts Ip_stats from `log_stats` in decending order
    based on request count and session count
    and returns the sorted lists in

    Parameters
    ----------
    log_stats: Log_stats
        input data
    bot: bool
        if `True` selects `log_stats.bots.stats` to be sorted and returned
        otherwise selects `log_stats.people.stats`

    Retrurns
    --------
    Tuple[List[Ip_stats], List[Ip_stats]]
        (<sorted based on requests count>, <sorted based on sessions count>)
    """
    if bot:
        stats = log_stats.bots.stats
    else:
        stats = log_stats.people.stats

    req_sorted_stats = sorted(
        stats.values(), key=lambda x: x.requests_num, reverse=True
    )
    sess_sorted_stats = sorted(
        stats.values(), key=lambda x: x.sessions_num, reverse=True
    )
    return (req_sorted_stats, sess_sorted_stats)


def print_most_frequent(
    html: Html_maker,
    req_sorted_stats: List[Ip_stats],
    sess_sorted_stats: List[Ip_stats],
    bots: bool,
    selected="",
    host_name=True,
    geoloc_db: Optional[GeolocDB] = None,
):
    html.append("<h3>Most frequent</h3>\n")
    uniq_classes = html.print_selection(
        ["session table", "requests table"], [[selected]] * 2
    )
    html.append("<div class='flex-align-start'>")

    if bots:
        group_name = "bots"
        header = [
            "Rank",
            "Bot's IP",
            "Host name",
            "Bot's url",
            "Geolocation",
            "Requests count",
            "Sessions count",
        ]
    else:
        group_name = "human users"
        header = [
            "Rank",
            "IP address",
            "Host name",
            "Geolocation",
            "Requests count",
            "Sessions count",
        ]

    html.append(
        make_table(
            f"Most frequent {group_name} by number of sessions",
            header,
            get_most_frequent_table_data(
                sess_sorted_stats,
                20,
                host_name=host_name,
                bots=bots,
                geoloc_db=geoloc_db,
            ),
            None,
            ["selectable", selected, uniq_classes[0]],
            attribs_for_most_freq_table(sess_sorted_stats, 20),
        )
    )

    html.append(
        make_table(
            f"Most frequent {group_name} by number of requests",
            header,
            get_most_frequent_table_data(
                req_sorted_stats,
                20,
                host_name=host_name,
                bots=bots,
                geoloc_db=geoloc_db,
            ),
            None,
            ["selectable", selected, uniq_classes[1]],
            attribs_for_most_freq_table(req_sorted_stats, 20),
        )
    )

    html.append("</div>")


def get_most_frequent_table_data(
    sorted_data: List[Ip_stats],
    n: int,
    bots: bool,
    host_name=True,
    geoloc_db: Optional[GeolocDB] = None,
) -> List[List]:
    """From decendingly sorted list of Ip_stats
    return list of `n` rows in most frequent table"""
    n = min(n, len(sorted_data))
    rows = []

    for i, ip_stat in enumerate(sorted_data[:n]):
        if host_name and ip_stat.host_name == "Unresolved":
            ip_stat.update_host_name()
        if ip_stat.geolocation == "Unresolved":
            ip_stat.update_geolocation(geoloc_db)

        row = [f"{i + 1}"]
        row.append(ip_stat.ip_addr)
        row.append(ip_stat.get_short_host_name())
        if bots:
            row.append(ip_stat.bot_url)
        row.append(ip_stat.geolocation)
        row.append(ip_stat.requests_num)
        row.append(ip_stat.sessions_num)

        rows.append(row)

    return rows


def attribs_for_most_freq_table(data: List[Ip_stats], n: int) -> List[List[str]]:
    """Returs attributes for `td` elements for most frequent table table"""
    n = min(n, len(data))

    return list(["", "", f"title='{data[i].host_name}'", "", "", ""] for i in range(n))


def print_day_distribution(log_stats: Log_stats, html: Html_maker, bots, selected=""):
    group_name = "bots" if bots else "users"

    html.append("<h3>Distribution of across hours of day</h3>")
    uniq_classes = html.print_selection(
        ["table", "session graph", "request graph"], [[selected]] * 3
    )

    data = log_stats.bots if bots else log_stats.people
    table_body = list(
        [
            f"{i}:00 - {i}:59",
            str(data.day_req_distrib[i]),
            str(data.day_sess_distrib[i]),
        ]
        for i in range(24)
    )
    table_body.append(
        ["Sum", str(sum(data.day_req_distrib)), str(sum(data.day_sess_distrib))]
    )

    html.append("<div class='flex-align-start'>")
    html.append(
        make_table(
            f"Distribution of {group_name} across hours of day",
            ["Time", "Request count", "Sessions count"],
            table_body,
            None,
            ["selectable", selected, uniq_classes[0]],
        )
    )

    html.append(f'<div class="selectable {selected} {uniq_classes[1]}">')
    print_distribution_graph(
        html,
        data.day_sess_distrib,
        "hours",
        "session count",
        [f"{i}:00 - {i}:59" for i in range(24)],
        group_name,
        left_margin=True,
    )
    html.append(f'</div>\n<div class="selectable {selected} {uniq_classes[2]}">')
    print_distribution_graph(
        html,
        data.day_req_distrib,
        "hours",
        "request count",
        [f"{i}:00 - {i}:59" for i in range(24)],
        group_name,
        left_margin=True,
    )
    html.append("</div></div>")


def print_week_distribution(
    log_stats: Log_stats, html: Html_maker, bots, selected=True
):
    group_name = "bots" if bots else "users"

    html.append("<h3>Distributions across week days</h3>")
    uniq_classes = html.print_selection(
        ["table", "session graph", "request graph"], [[selected]] * 3
    )

    data = log_stats.bots if bots else log_stats.people
    table_body = list(
        [DAYS[i], str(data.week_req_distrib[i]), str(data.week_sess_distrib[i])]
        for i in range(7)
    )
    table_body.append(
        ["Sum", str(sum(data.week_req_distrib)), str(sum(data.week_sess_distrib))]
    )

    html.append("<div class='flex-align-start'>")
    html.append(
        make_table(
            f"Distributions of {group_name} across week days",
            ["Day", "Request count", "Sessions count"],
            table_body,
            None,
            ["selectable", selected, uniq_classes[0]],
        )
    )

    html.append(f'<div class="selectable {selected} {uniq_classes[1]}">')
    print_distribution_graph(
        html, data.week_sess_distrib, "days of week", "session count", DAYS, group_name
    )
    html.append(f'</div>\n<div class="selectable {selected} {uniq_classes[2]}">')
    print_distribution_graph(
        html, data.week_req_distrib, "days of week", "request count", DAYS, group_name
    )
    html.append("</div></div>")


def print_month_distributions(
    log_stats: Log_stats, html: Html_maker, bots: bool, selected: str = ""
):
    group_name = "bots" if bots else "users"

    html.append("<h3>Distributions accross months</h3>")
    uniq_classes = html.print_selection(
        ["sessions graph", "requests graph"], [[selected]] * 2
    )

    html.append(
        f'<div class="flex-align-start">\n<div class="selectable {selected} {uniq_classes[0]}">'
    )

    data = log_stats.bots if bots else log_stats.people
    session_distrib = sorted(data.month_sess_distrib.items(), key=lambda x: x[0])

    distrib_values = list(map(lambda x: x[1], session_distrib))
    distrib_keys = list(map(lambda x: x[0], session_distrib))
    print_distribution_graph(
        html,
        distrib_values,
        "months",
        "session count",
        [f"{MONTHS[k[1]]} {k[0]}" for k in distrib_keys],
        group_name,
        left_margin=True,
    )

    html.append(f'</div>\n<div class="selectable {selected} {uniq_classes[1]}">')

    request_distrib = sorted(data.month_req_distrib.items(), key=lambda x: x[0])
    distrib_values = list(map(lambda x: x[1], request_distrib))
    distrib_keys = list(map(lambda x: x[0], request_distrib))

    print_distribution_graph(
        html,
        distrib_values,
        "months",
        "request count",
        [f"{MONTHS[k[1]]} {k[0]}" for k in distrib_keys],
        group_name,
        left_margin=True,
    )
    html.append("</div>\n</div>")


def print_distribution_graph(
    html: Html_maker,
    data: List[float],
    xlabel: str,
    ylabel: str,
    x_ticks_labels: List[float],
    group_name: str,
    left_margin: bool = False,
) -> None:
    """Creates distribution horizonatl bar graph from `data` as .svg
    and appends it to `html`

    Parameters
    ----------
    html: Html_maker
    data: List[float]
        list of frequescies sorted in decending order
    xlabel: str
    ylabel: str
    x_ticks_labels: List[float]
        list of data labels correspoding to `data`
    group_name: str
    left_margin: bool, optional
        default: `False`

    """
    data = list(reversed(data))
    x_ticks_labels = list(reversed(x_ticks_labels))

    _print_h_bar_graph(
        html,
        xs=data,
        ys=list(range(len(data))),
        xlabel=ylabel,
        ylabel=xlabel,
        title=f"Distribution of {group_name} across {xlabel}",
        y_tick_lables=x_ticks_labels,
        left_margin=left_margin,
    )


def get_geolocations_from_sample(
    sample: List[Ip_stats], geoloc_db: Optional[GeolocDB] = None
) -> List[Tuple[str, float]]:
    """
    Returns
    -------
    List[Tuple[str,float]
        decreasingly sorted list of tuples
        `(<geolocation>, <proportion of the location in the sample weighted by sessions counts>)`
    """

    geoloc_weights = {}
    weights_sum = 0

    for ip_stat in sample:
        if ip_stat.geolocation == "Unresolved":
            ip_stat.update_geolocation(geoloc_db)

        weight = geoloc_weights.get(ip_stat.geolocation, 0)
        weight += ip_stat.sessions_num
        geoloc_weights[ip_stat.geolocation] = weight
        weights_sum += ip_stat.sessions_num

    return sorted(
        map(lambda x: (x[0], 100 * x[1] / weights_sum), geoloc_weights.items()),
        key=lambda x: x[1],
        reverse=True,
    )


def _test_geolocation(
    log_stats,
    html: Html_maker,
    geoloc_sample_size: int,
    repetitions: int = 5,
    selected: bool = False,
    err_msg: bool = False,
    geoloc_db: Optional[GeolocDB] = None,
):
    # now olnly for human users
    def filter_f(stat: Ip_stats) -> bool:
        return stat.sessions_num <= 50

    data: List[Ip_stats] = list(filter(filter_f, log_stats.people.stats.values()))

    samples: List[List[Ip_stats]] = []
    sample_size = min(len(data), geoloc_sample_size)

    for _ in range(repetitions):
        if len(data) > sample_size:
            samples.append(random.sample(data, sample_size))
        else:
            samples.append(data)

    # geolocation
    timer = Ez_timer("geolocations", verbose=err_msg)

    geoloc_stats = []
    for i, sample in enumerate(samples):
        timer2 = Ez_timer(f"geolocaion {i+1}", verbose=False)
        geoloc_stats.append(get_geolocations_from_sample(sample, geoloc_db))
        timer2.finish(err_msg)

    timer.finish(err_msg)

    # Printing
    selected = "selected" if selected else ""

    html.append("<h3>Estimated locations</h3>")
    button_names = [f"geoloc{i}" for i in range(1, repetitions + 1)]
    uniq_classes = html.print_selection(
        button_names, [["selectable", selected]] * repetitions
    )

    # print geolocation
    html.append('<div class="flex-align-start">')
    for i in range(repetitions):
        html.append(f'<div class="selectable {selected} {uniq_classes[i]}">')
        print_geolocations_graph(
            html, geoloc_stats[i], "Geolocation", left_margin=True, max_size=20
        )
        html.append("</div>")
    html.append("</div>")


def print_countries_stats(
    log_stats: Log_stats,
    html: Html_maker,
    sample_size: int,
    selected: bool = False,
    geoloc_db: Optional[GeolocDB] = None,
    err_msg: bool = False,
):
    """Estimates the geolocations of human users from `log_stats`
    on a random sample of length `sample_size`.
    The porportions of the geolocations in the sample are weighted by
    the number of sessions of the IP adresses from given location.
    Beacuse of this, the sample is taken (if enough data)
    only from IP addresses with number of sessions <= 50.

    Appends to `html`:
        - table of all geolocations from server
          and their weighted proportions in the sample
        - horizontal bar graph of the geolocations sahres in the sample
    """
    # TODO move making sample and estimating geolocations elsewhere??

    if sample_size <= 0:
        return

    sample: List[Ip_stats] = list(
        filter(
            lambda ip_stat: ip_stat.sessions_num <= 50, log_stats.people.stats.values()
        )
    )

    sample_size = min(len(sample), sample_size)
    if len(sample) > sample_size:
        sample = random.sample(sample, sample_size)
    else:
        sample_size = len(sample)

    # estimate geolocations
    if err_msg:
        timer = Ez_timer("geolocation")

    estimated_locations = get_geolocations_from_sample(sample, geoloc_db)

    if err_msg:
        timer.finish()

    # making html
    selected = "selected" if selected else ""

    html.append("<h3>Estimated locations</h3>")
    uniq_classes = html.print_selection(
        ["Geoloc table", "Geoloc graph"], [[selected]] * 2
    )

    # geolocation table
    html.append('<div class="flex-align-start">')
    html.append(
        f'<div class="selectable {selected} {uniq_classes[0]} flex-col-center">'
    )

    table_body = list(
        [i + 1, country, round(value, 2)]
        for i, (country, value) in enumerate(estimated_locations)
    )
    html.append(
        make_table(
            "Most frequent geolocations",
            ["Rank", "Geolocation", "Percetns"],
            table_body,
        )
    )
    html.append(
        '<a href="http://www.geoplugin.com/geolocation/">IP Geolocation</a>'
        ' by <a href="http://www.geoplugin.com">geoPlugin</a>\n</div>'
    )

    # geolocation graph
    html.append(
        f'<div class="selectable {selected} {uniq_classes[1]} flex-col-center">'
    )
    print_geolocations_graph(
        html, estimated_locations, "Geolocation", left_margin=True, max_size=10
    )
    html.append(
        '<a href="http://www.geoplugin.com/geolocation/">IP Geolocation</a>'
        ' by <a href="http://www.geoplugin.com">geoPlugin</a>\n</div>'
    )
    html.append("</div>")


def print_geolocations_graph(
    html: Html_maker,
    sorted_data: List[Tuple[str, float]],
    title: str,
    left_margin: bool = False,
    max_size: Optional[int] = None,
):
    """Appends geolocation graph to `html`

    Parameters
    ----------
    html: Html_maker
    sorted_data: List[Tuple[str, float]]
        decreasingly sorted list of tuples
        `(<geolocation>, <proportion of the location>)`
    title: str
    left_margin: bool, optional
        default: `False`
    max_size: int, optional
        defaultL `None`

    """
    rest_sum = 0
    if max_size is not None and len(sorted_data) > max_size:
        rest_sum = sum(map(lambda x: x[1], sorted_data[max_size:]))
        sorted_data = sorted_data[:max_size]

    sorted_country_names = []
    sorted_country_percents = []

    for name, percent in sorted_data:
        sorted_country_names.append(name)
        sorted_country_percents.append(percent)

    if rest_sum > 0:
        sorted_country_names.append("other")
        sorted_country_percents.append(rest_sum)

    _print_h_bar_graph(
        html,
        sorted_country_percents,
        list(range(len(sorted_country_names))),
        "Percents",
        "",
        title,
        sorted_country_names,
        left_margin,
    )


def _print_h_bar_graph(
    html: Html_maker,
    xs,
    ys,
    xlabel,
    ylabel,
    title,
    y_tick_lables,
    left_margin: bool = False,
):
    """Appends horizontal bar graph to `html` as .svg using matplotlib

    Parameters
    ----------
    html: Html_maker
    xs: array-like
        widths of the bars
    ys: array-like
        y coordinates of the bars
    xlabel: str
    ylabel: str
    title: str
    y_tick_lables: List[str]
    left_margin: bool, optional
        default: `False`
    """
    # set height of the graph, this somehow works
    x, y = plt.rcParams["figure.figsize"]
    y = y * len(ys) / 12
    if len(ys) < 10:
        y += 3
    plt.rcParams["figure.figsize"] = (x, y)

    fig, ax = plt.subplots()
    ax.ticklabel_format(axis="x", style="sci", scilimits=(-4, 4), useOffset=False)
    ax.barh(y=ys, width=xs, align="center")

    for i, x in enumerate(xs):
        plt.annotate(
            str(round(x, 2)),
            (x, i),
            horizontalalignment="left",
            verticalalignment="center",
        )
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_yticks(ys)
    ax.set_yticklabels(y_tick_lables)
    if left_margin:
        plt.subplots_adjust(left=0.25)

    with io.StringIO() as f:
        plt.savefig(f, format="svg")
        html.append(f.getvalue())
    plt.clf()
    plt.close(fig)
    plt.rcParams["figure.figsize"] = plt.rcParamsDefault["figure.figsize"]


def make_histogram(log_stats: Log_stats, file_name: str, selected: str = ""):
    # For people only!!

    with open(
        f"{os.path.dirname(__file__)}/hist.js", "r"
    ) as f:  # TODO: think of better way to get hist.js
        js = f.read()
    template = "<html><head><style>{css}</style> <script>{js}</script></head>\n<body>\n{content}\n</body>\n</html>"
    html: Html_maker = Html_maker(template, js=js)

    html.append("<h1>Histograms</h1>")

    for year in sorted(log_stats.year_stats.keys()):
        log_stats.switch_year(year)
        print_histograms_for_stats(
            stats=log_stats.people.stats.values(),
            html=html,
            title=f"Year {year}",
            selected=selected,
        )

    plt.close("all")

    with open(file_name, "w") as f:
        f.write(html.html())


def print_histograms_for_stats(
    stats: List[Ip_stats], html: Html_maker, title: str, selected: str = ""
):
    session_data = []
    request_data = []

    for stat in stats:
        session_data.append(stat.sessions_num)
        request_data.append(stat.requests_num)

    html.append(f"<h2>{title}</h2>")
    selected = "selected" if selected else ""

    # sessions
    html.append("<h3>Session histogram</h3>")
    uniq_classes = html.print_selection(
        ["Full histogram", "Detailed histogram", "Table"], [[selected]] * 3
    )
    html.append("<div class='flex-align-start'>")

    _print_histogram_graphs(
        html=html,
        data=session_data,
        bins=300,
        cutoff_for_detail=300,
        xlabel="Session count",
        uniq_classes=uniq_classes,
    )

    bins = get_splited_data(session_data, dellims=[2, 5, 10, 50, 100, 1000])
    print_splitted_vals_table(
        bins,
        html=html,
        delims=[2, 5, 10, 50, 100, 1000],
        data_name="sessions",
        selected=selected,
    )
    html.append("</div>")

    # requests
    html.append("<h3>Requests histogram</h3>")
    uniq_classes = html.print_selection(
        ["Full histogram", "Detailed histogram", "Table"], [[selected]] * 3
    )
    html.append("<div class='flex-align-start'>")

    _print_histogram_graphs(
        html=html,
        data=request_data,
        bins=500,
        cutoff_for_detail=800,
        xlabel="Request count",
        uniq_classes=uniq_classes,
        selected=selected,
    )

    bins = get_splited_data(request_data, delims=[2, 5, 10, 50, 100, 1000, 10000])
    print_splitted_vals_table(
        bins,
        html=html,
        delims=[2, 5, 10, 50, 100, 1000, 10000],
        data_name="requests",
        selected=selected,
    )
    html.append("</div>")

    # top users
    print_most_frequent(
        html,
        sorted(stats, key=lambda x: x.requests_num, reverse=True),
        sorted(stats, key=lambda x: x.sessions_num, reverse=True),
        bots=False,
        selected=selected,
        host_name=False,
    )


def _print_histogram_graphs(
    html: Html_maker,
    data: List[int],
    bins: int,
    cutoff_for_detail: int,
    xlabel: str,
    uniq_classes: List[str] = ["", ""],
    selected="",
) -> None:
    """Creates two histograms from `data` and appends them to `html`.
    First histogram is regular histogram:
    devides the range of `data` (max(data)-min(data)) into `bins` number of bins (x-axis),
    and plots the number of data in each bin (y-axis).

    Second histogram is just zoomed and cutted view of the first histogram,
    so that x axis ends in value `cutoff_for_detail`.

    Parameters
    ----------
    html: Html_maker
    data: List[int]
    bins: int
        number of bins which the data will be devided in
    cutoff_for_detail: int
        the maximal value on x-axis for the second histogram
    xlabel: str
    uniq_classes: List[str], optional
        default: `['', '']`;
        list of unique classes used by selection buttons
        to show/hide the two created histograms
    selected: str
        default: `""`;
        - if `""` histograms will be hidden by default,
        - if `"selected"` histograms will be shown by default
    """
    _, ax = plt.subplots()
    ax.hist(data, bins=bins, log=True, histtype="stepfilled")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Ip address count")
    ax.set_title("Full histogram")

    html.append(f"<div class='{uniq_classes[0]} selectable {selected}'>")
    with io.StringIO() as f:
        plt.savefig(f, format="svg")
        html.append(f.getvalue())
    html.append("</div>")

    ax.set_xlim(left=-10, right=cutoff_for_detail)
    ax.set_title("Detailed histogram")

    html.append(f"<div class='{uniq_classes[1]} selectable {selected}'>")
    with io.StringIO() as f:
        plt.savefig(f, format="svg")
        html.append(f.getvalue())
    plt.clf()
    html.append("</div>")


def get_splited_data(data: List[int], delims: List[int]) -> List[List[int]]:
    """Splits values in `data` into `len(delim)+1` bins, s.t.
    i-th bin contains values form `data` that statisfies `delim[i-1]` <= value < `delim[i]`,
    0-th bin contains values that are less than delim[0],
    last bin contains values larger or equal to `delims[-1]`.

    Parameters
    ----------
    data: List[int]
    delims: List[int]
        i-th element (List[int]) represents i-th bin

    Returns
    -------
    List[List[int]]

    """
    categories = [[] for _ in range(len(delims) + 1)]

    for val in data:
        for i in range(len(delims)):
            if val < delims[i]:
                categories[i].append(val)
                break
        else:
            categories[-1].append(val)

    return categories


def print_splitted_vals_table(
    splited_data: List[List[int]],
    html: Html_maker,
    delims: List[int],
    data_name: str = "ip addresses",
    uniqe_class: str = "",
    selected: str = "",
) -> None:
    """Prints table to `html` created from `splitted data`.
    Each row in table is a bin from `splited_data`
    The table has following colums:
        - Frequency [from, to]: range of i-th bin
        - Sum of `data_name`: sum if values in i-th bin
        - Sum [%]: sum if i-th bin relative to the sum of all bins
        - Unique IPs: number of values in i-th bin
        - Unique IPs [%]: number of values in i-th bin relative to the number of values in all bins

    Parameters
    ----------
    splited_data: List[List[int]]
        List of bins of data (List[int]),
        such list can be obtain by function get_splited_data
    html: Html_maker
    delims: List[int]
        delimeters separeting bins in `splited_data`
    data_name: str, optional
        default: `"ip addresses"`;
        name of the values in bins in `splited_data`
    uniqe_class: str, optional
        default: `""`;
        unique class used by selection button
        to show/hide the table
    selected: str
        default: `""`;
        - if `""` table will be hidden by default,
        - if `"selected"` table will be shown by default

    """
    data_sums = list(map(sum, splited_data))
    tot_sum = sum(data_sums)
    tot_len = sum(map(len, data_sums))

    table_body = []
    prev_delim = 0

    for i in range(len(delims)):
        table_body.append(
            [
                f"{prev_delim} to {delims[i]-1}",
                data_sums[i],
                round(100 * data_sums[i] / tot_sum, 1),
                len(splited_data[i]),  # unique ip addresess
                round(
                    100 * len(splited_data[i]) / tot_len, 1
                ),  # unique ip addresess in %
            ]
        )
        prev_delim = delims[i]

    table_body.append(
        [
            f"Above {delims[-1]}",
            data_sums[-1],
            round(100 * data_sums[-1] / tot_sum, 1),
            len(splited_data[-1]),
            round(100 * len(splited_data[-1]) / tot_len, 1),
        ]
    )
    table_body.append(["Total", tot_sum, 100, tot_len, 100])

    html.append(f"<div class='{uniqe_class} selectable {selected}'>")
    html.append(
        make_table(
            f"{data_name.capitalize()} splitted into bins",
            [
                "Frequency [from, to]",
                f"Sum of {data_name}",
                "Sum [%]",
                "Unique IPs",
                "Unique IPs [%]",
            ],
            table_body,
        )
    )
    html.append("</div>")


# def anotate_bars(xs: List[float], ys: List[float], labels: List[int], rotation: int):
#     for i, x in enumerate(xs):
#         plt.annotate(str(labels[i]), (x, ys[i]),
#                      rotation=rotation, horizontalalignment='center')
