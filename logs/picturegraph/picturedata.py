from typing import NamedTuple, List


class GraphValue(NamedTuple):
    """Data structure to strore data for a single value
    in overview picture graph.
    Attribures
    ----------
    x_step: int
        width of the collumn in graph for this value
    value: int
        usually number of requests or sessions or unique ip adresses
    label: str
        label of the value
    outlier: bool
    """

    x_step: int
    value: int
    label: str
    outlier: bool = False


Graph_data = List[GraphValue]
"""Contains `GraphValues` in their x-axis order"""
