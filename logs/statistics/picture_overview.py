from logs.statistics.processing import Log_stats, Daily_stats
from typing import List, Union, Dict
import json
from logs.picturegraph.picturedata import Graph_data, Graph_value
from logs.picturegraph.makepicture import make_picture
from logs.statistics.constants import MONTHS
BASE_STEP = 2 # px


def make_pictures(stats: Union[Log_stats, str], output_json="",
                  separate_years: List[int] = []):
    """Makes overview pictures
    
    Parameters
    ----------
    stats: Log_stats | str
        source of data for the overview pictures.
        If `Log_stats`, the data for the pictures will be
        obtained from it.
        If `str`, then it is a path to the json file
        with saved data for overview pictures.
    output_json: str, optional
        default: `""`; string of the path to file,
        to which save the data for the pictures as json.
        If `""`, then no data will be saved.
    """
    metrics = ("requests", "ips", "sessions")
    data: Dict[str, Graph_data]

    if isinstance(stats, str):
        with open(stats, "r") as data_f:
            data = json.load(data_f) # TODO

    else:
        sorted_daily_data = sorted(stats.daily_data.values(), key=lambda daily_stats: daily_stats.date)
        data = {}

        for metric in metrics:
            data[f"day_{metric}"] = daily_data_to_graph_data(
                sorted_daily_data,
                metric=metric,
                base_step=BASE_STEP
            )
            data[f"month_{metric}"] = day_to_month_data(data[f"day_{metric}"])
            data[f"day_{metric}"] = mark_outliers(data[f"day_{metric}"], len(data[f"month_{metric}"]))

    if output_json != "":
        with open(output_json, "w") as output_f:
            json.dump(data, output_f)
    
    for metric in metrics:
        month_data = month_labels_to_year_labels(data[f"month_{metric}"])
        day_data = prettify_day_labels(data[f"day_{metric}"])
        
        make_picture(
            data=day_data,
            right_data=month_data,
            y_axis_name="per day",
            right_y_axis_name="per month",
            output_name=f"{metric}_overview.png",
            title=metric
        )

    for year in separate_years:
        year = str(year)

        for metric in metrics:
            day_data = list(filter(
                lambda graph_value: year in graph_value.label,
                data[f"day_{metric}"]
            ))
            month_data = list(filter(
                lambda graph_value: year in graph_value.label,
                data[f"month_{metric}"]
            ))

            make_picture(
                data=prettify_day_labels(day_data),
                right_data=prettify_month_labels(month_data),
                y_axis_name="per day",
                right_y_axis_name="per month", 
                output_name=f"{metric}_{year}_overview.png",
                title=f"{year} {metric}"
            )
        

def daily_data_to_graph_data(
        sorted_daily_data: List[Daily_stats],
        metric: str,
        base_step: int
    ) -> Graph_data:
    """Transforms `sorted_daily_data` to `Graph_data`.

    Parameters
    ----------
    sorted_daily_data: List[Daily_stats]
        Daily_stats in the same order as they should appear in graph
    metric: str
        takes values: "requests" | "sessions" | "ips";
        - if "requests", then values in the returned Graph_data
        corresponds to number of requests in given day
        - if "sessions", then values in the returned Graph_data
        corresponds to number of sessions in given day
        - if "ips", then values in the returned Graph_data
        corresponds to number uniques IP adresses in given day
    base_step: int
        x_step value for Graph_values in returned Graph_value
    
    Returns
    -------
    Graph_data
        Contains its values in the same order as `sorted_daily_data`.
        Each value `v` is Graph_value with:
        `v.x_step` set to `base_step`,
        `v.value` set based on `metrcic`,
        `v.label` set to date string in isoformat
         of corresponding daily_stat.date
    """
    if metric == "requests":
        return list(map(
            lambda daily_stats:
                Graph_value(base_step,
                            daily_stats.requests,
                            daily_stats.date.isoformat()
            ),
            sorted_daily_data
        ))
    
    if metric == "sessions":
        return list(map(
            lambda daily_stats:
                Graph_value(base_step,
                            daily_stats.sessions,
                            daily_stats.date.isoformat()
            ),
            sorted_daily_data
        ))

    if metric == "ips":
        return list(map(
            lambda daily_stats:
                Graph_value(base_step,
                            len(daily_stats.ips),
                            daily_stats.date.isoformat()
            ),
            sorted_daily_data
        ))
    
    raise ValueError("Unknown metric %s", (metric))


def day_to_month_data(data: Graph_data) -> Graph_data:
    """Transforms Graph_data for days into Graph_data for months
    
    Parameters
    ----------
    data: Graph_data
        contais graph_values for days.
        The graph_values has to have date in isoformat as their labels,
        in order to create correct labels in in return Graph_value.
    
    Returns
    -------
    Graph_data
        its Graph_values are set so:
        `x_step` is the sum of x_steps of the days in given month,
        `value` is the sum of values of the days in given month,
        `label` is month in format "%Y-%m"
    """
    month_data = []

    current_month = None
    month_value = 0
    month_width = 0

    for width, value, date, _ in data:
        split_date = date.split("-")  # date is isoformat
        month = f"{split_date[0]}-{split_date[1]}"

        if month != current_month:
            if current_month is not None:
                month_data.append(Graph_value(month_width, month_value, current_month))
                month_value, month_width = 0, 0
            current_month = month

        month_width += width
        month_value += value

    month_data.append(Graph_value(month_width, month_value, current_month))
    return month_data


def month_labels_to_year_labels(month_data: Graph_data) -> Graph_data:
    """Changes labels of the graph_values in `month_data`
    which are the first values for their year to the year.
    Labels of other graph_values are set to an empty string.
    """
    result_data = []

    current_year = None
    for w, h, month, _ in month_data:
        label = ""

        if month[:4] != current_year:
            current_year = month[:4]
            label = current_year
        
        result_data.append(Graph_value(w, h, label))

    return result_data


def mark_outliers(day_data: Graph_data, month_count: int):
    """Outliers are calssifies as follows:
        - `month_count // 4` maximal values are 
        seen as potential outliers (circa 3 potential outlier per year)
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

    outliers_count = month_count // 4
    sorted_values = sorted(map(lambda graph_val: graph_val.value, day_data))

    med = sorted_values[len(sorted_values) // 2]
    maximal_nonoutlier_value = sorted_values[outliers_count]

    while outliers_count > 0 and sorted_values[outliers_count-1] < 3*med:
        maximal_nonoutlier_value = sorted_values[outliers_count-1]
        outliers_count -= 1

    return list(map(
        lambda graph_value: Graph_value(
            graph_value.x_step,
            graph_value.value,
            graph_value.label,
            graph_value.value > maximal_nonoutlier_value),
        day_data
    ))


def prettify_month_labels(data: Graph_data) -> Graph_data:
    """sets prettier label for evry graph_value in `data`.
    The prettier label is in format '<abbreviated month name> <year>' 
    
    Parameters
    ----------
    data: Graph_data
        expected label of each graph_value is "<month as a number>-<year>" 
        or an empty string"""
    return list(map(
        lambda graph_value: Graph_value(
            graph_value.x_step,
            graph_value.value,
            prettify_date_str(graph_value.label),
            graph_value.outlier),
        data
    ))
    

def prettify_date_str(date: str) -> str:
    date = date.split("-")
    pretty_month = MONTHS[int(date[1])] if len(date) > 1 else ""
    
    return f"{pretty_month} {date[0]}"


def prettify_day_labels(data: Graph_data) -> Graph_data:
    """sets label for evry graph_value in `data` to an empty string"""
    return list(map(
        lambda graph_value: Graph_value(
            graph_value.x_step,
            graph_value.value,
            "",
            graph_value.outlier),
        data
    ))
