import datetime
from typing import Callable, Dict, List, Optional

from logs.picturegraph.makepicture import make_picture
from logs.picturegraph.picturedata import Graph_data, GraphValue
from logs.statistics.constants import MONTHS
from logs.statistics.dailystat import SimpleDailyStats
from logs.statistics.cache import merge_simple_dailydata


BASE_STEP = 2  # px


def make_pictures(
    simple_daily_data: List[SimpleDailyStats],
    cached_daily_data: List[SimpleDailyStats] = [],
    years: List[int] = [],
    name: Optional[str] = None,
    purge_years: bool = True,
):
    """Makes overview pictures.

    Parameters
    ----------
    simple_daily_data: List[SimpleDailyStats]
        source data for the overview pictures.
    cached_daily_data: List[SimpleDailyStats], optional
        default: `[]`; cache data,
        which merged with the `simple_daily_data`.
    years: List[int], optional
        default: empty list; years specified to make overview pictures from
    purge_years: bool, optional
        default: `True`; if True only years from `years`
        will be included in the ovetview pictures from all years
    """
    metrics = ("requests", "ips", "sessions")
    data: Dict[str, Graph_data]

    sorted_daily_data = merge_simple_dailydata(
        older=cached_daily_data,
        newer=sorted(simple_daily_data, key=lambda daily_stats: daily_stats.date),
    )
    data = {}

    for metric in metrics:
        # create graph data
        data[f"day_{metric}"] = daily_data_to_day_graph_data(
            sorted_daily_data, metric=metric, base_step=BASE_STEP
        )
        data[f"month_{metric}"] = daily_data_to_month_graph_data(
            sorted_daily_data, metric=metric, base_step=BASE_STEP
        )
        data[f"day_{metric}"] = mark_outliers(
            data[f"day_{metric}"], len(data[f"month_{metric}"])
        )

        title = f"{name} - {metric}" if name is not None else metric
        purged_data = {}

        # create distinct picture each year
        for year in years:
            year = str(year)

            day_data = list(
                filter(
                    lambda graph_value: year in graph_value.label, data[f"day_{metric}"]
                )
            )
            month_data = list(
                filter(
                    lambda graph_value: year in graph_value.label,
                    data[f"month_{metric}"],
                )
            )          
            make_picture(
                data=remove_labels(day_data),
                right_data=prettify_month_labels(month_data),
                y_axis_name="per day",
                right_y_axis_name="per month",
                output_name=f"{metric}_{year}_overview.png",
                title=title,
            )

            p_data = purged_data.get(f"day_{metric}", [])
            p_data += day_data
            purged_data[f"day_{metric}"] = p_data

            p_data = purged_data.get(f"month_{metric}", [])
            p_data += month_data
            purged_data[f"month_{metric}"] = p_data
        
        # create picture for all years
        if purge_years:
            data = purged_data
        
        month_data = month_labels_to_year_labels(data[f"month_{metric}"])
        day_data = remove_labels(data[f"day_{metric}"])

        make_picture(
            data=day_data,
            right_data=month_data,
            y_axis_name="per day",
            right_y_axis_name="per month",
            output_name=f"{metric}_overview.png",
            title=metric,
        )




def daily_data_to_day_graph_data(
    sorted_daily_data: List[SimpleDailyStats], metric: str, base_step: int
) -> Graph_data:
    """Transforms `sorted_daily_data` to `Graph_data`. Raises ValueError

    Parameters
    ----------
    sorted_daily_data: List[SimpleDailyStats]
        SimpleDailyStats in the same order as they should appear in graph
    metric: str
        takes values: "requests" | "sessions" | "ips";
        - if "requests", then values in the returned Graph_data
        corresponds to number of requests in given day
        - if "sessions", then values in the returned Graph_data
        corresponds to number of sessions in given day
        - if "ips", then values in the returned Graph_data
        corresponds to number uniques IP adresses in given day
        - raises ValueError if other value is given
    base_step: int
        x_step value for GraphValues in returned GraphValue

    Returns
    -------
    Graph_data
        Contains its values in the same order as `sorted_daily_data`.
        Each value `v` is GraphValue with:
        `v.x_step` set to `base_step`,
        `v.value` set based on `metrcic`,
        `v.label` set to daily_data.date.isoformat()
    """
    return list(
        map(
            lambda daily_stats: GraphValue(
                base_step,
                daily_stats.__getattribute__(metric),
                daily_stats.date.isoformat(),
            ),
            sorted_daily_data,
        )
    )


def date_format(date: datetime.date) -> str:
    return f"{MONTHS[date.month]} {date.year}"


def daily_data_to_month_graph_data(
    sorted_daily_data: List[SimpleDailyStats],
    metric: str,
    base_step: int,
    label_format: Callable[
        [datetime.date], str
    ] = date_format ,
) -> Graph_data:
    """Transforms `sorted_daily_data` to `Graph_data`,
    groups consequent data on months,
    eg. sums consequent day values belonging to the same month into one month value.
    Raises ValueError

    Parameters
    ----------
    sorted_daily_data: List[SimpleDailyStats]
        SimpleDailyStats in the same order as they should appear in graph
    metric: str
        takes values: "requests" | "sessions" | "ips";
        - if "requests", then values in the returned Graph_data
        corresponds to number of requests in given day
        - if "sessions", then values in the returned Graph_data
        corresponds to number of sessions in given day
        - if "ips", then values in the returned Graph_data
        corresponds to number uniques IP adresses in given day
        - raises ValueError if other value is given
    base_step: int
        x_step value for GraphValues in returned GraphValue
    label_format: Callable[[datetime.date], str], optional
        function mapping datetime.date onject to date string,
        defualt format is "<Month> <Year>"

    Returns
    -------
    Graph_data
        Each value `v` is GraphValue with:
        - `v.x_step` set to `base_step` * nummber of days in the month,
        `v.value` set to the sum of values in the days of the month,
        - based on `metrcic`,
        - `v.label` set based on `label_format`
    """

    result_data = []
    if len(sorted_daily_data) < 1:
        return result_data

    current_date = sorted_daily_data[0].date
    month_width = base_step
    month_value = sorted_daily_data[0].__getattribute__(metric)

    for dd in sorted_daily_data[1:]:
        if dd.date.month != current_date.month:
            result_data.append(
                GraphValue(month_width, month_value, label_format(current_date))
            )
            month_width, month_value = 0, 0

        month_width += base_step
        month_value += dd.__getattribute__(metric)
        current_date = dd.date
    
    result_data.append(
                GraphValue(month_width, month_value, label_format(current_date))
            )

    return result_data


def label_to_year(label: str) -> str:
    return label.split()[1]


def month_labels_to_year_labels(
    month_data: Graph_data,
    year_from_label: Callable[[str], str] = label_to_year,
) -> Graph_data:
    """Changes labels of the graph_values in `month_data`
    which are the first values for their year to the year.
    Labels of other graph_values are set to an empty string.
    """
    result_data = []

    if len(month_data) < 1:
        return result_data

    result_data.append(month_data[0])
    current_year = year_from_label(month_data[0].label)

    for w, h, label, _ in month_data[1:]:

        year = year_from_label(label)
        if year != current_year:
            current_year = year
            label = current_year
        else:
            label = ""


        result_data.append(GraphValue(w, h, label))

    return result_data


def mark_outliers(day_data: Graph_data, month_count: int):
    """Outliers are calssifies as follows:
        - `5 * month_count // 12` maximal values are
        seen as potential outliers (circa 5 potential outlier per year)
        - From potential outliers are marked as outlier those
        whose value is grater than 3 times median of values of `day_data`
    Parameters
    ----------
    day_data: Graph_data
        contains graph_values for days
    month_count: int
        needed for classifing outliers

    Returns
    -------
    Graph_data
        contains the same graph_values,
        just those marked as outliers has their `outlier` field set to `True`
    """

    outliers_count = 5 * month_count // 12
    sorted_values = sorted(
        map(lambda graph_val: graph_val.value, day_data), reverse=True
    )

    med = sorted_values[len(sorted_values) // 2]
    maximal_nonoutlier_value = sorted_values[outliers_count]

    while outliers_count > 0 and sorted_values[outliers_count - 1] < 3 * med:
        maximal_nonoutlier_value = sorted_values[outliers_count - 1]
        outliers_count -= 1

    return list(
        map(
            lambda graph_value: GraphValue(
                graph_value.x_step,
                graph_value.value,
                graph_value.label,
                graph_value.value > maximal_nonoutlier_value,
            ),
            day_data,
        )
    )


def prettify_month_labels(data: Graph_data) -> Graph_data:
    """sets prettier label for evry graph_value in `data`.
    The prettier label is in format '<abbreviated month name> <year>'

    Parameters
    ----------
    data: Graph_data
        expected label of each graph_value is "<month as a number>-<year>"
        or an empty string"""
    return list(
        map(
            lambda graph_value: GraphValue(
                graph_value.x_step,
                graph_value.value,
                prettify_date_str(graph_value.label),
                graph_value.outlier,
            ),
            data,
        )
    )


def prettify_date_str(date: str) -> str:
    date = date.split("-")
    pretty_month = MONTHS[int(date[1])] if len(date) > 1 else ""

    return f"{pretty_month} {date[0]}"


def remove_labels(data: Graph_data) -> Graph_data:
    """sets label for every graph_value in `data` to an empty string"""
    return list(
        map(
            lambda graph_value: GraphValue(
                graph_value.x_step, graph_value.value, "", graph_value.outlier
            ),
            data,
        )
    )
