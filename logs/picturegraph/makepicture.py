from logs.picturegraph.pildata import PilData
from logs.picturegraph.helpers import get_text_size, draw_label
from PIL import Image, ImageDraw, ImageFont
from typing import Iterator, Optional
from logs.picturegraph.picturedata import Graph_data


def make_picture(
    data: Graph_data,
    output_name: str,
    right_data: Optional[Graph_data] = None,
    y_axis_name="",
    right_y_axis_name="",
    title="",
    ticks=5,
    spacing=0,
    right_spacing=0,
    left_margin=70,
    right_margin=70,
    bottom_margin=70,
    top_margin=80,
    height=800,
):
    """Makes a simple vertical bar graph of `right_data` and `data`,
    `right_data` if given will be plotted behind the `data` in gray color.
    Created graph is saved as svg into file with path `output_name`


    Parameters
    ----------
    data: Graph_data
    output_name: str
        path to output file in which graph pictuture will be saved as svg
    right_data: Graph_data, optional
        data which will be plotted behind `data`
    y_axis_name: str, optional
        default: `""`; name for "left" y-axis corresponding to `data`
    right_y_axis_name: str, optional
        default: `""`; name for "right" y-axis corresponding to `right_data`
    spacing: int, optional
        default: 0; x-axis spaces between plotted values from `data`
    right_spacing: int, optional
        default: 0; x-axis spaces between plotted values from `right_data`
    title: str, optional
        default: `""`; title of the graph
    ticks: int, optional,
        default: 5; number of ticks on y-axes
    left_margin: int
        default: 70; size of the left margin in pixels,
        make sure it is large enough to fit `y_axis_name`
    right_margin: int
        default: 70; size of the right margin in pixels,
        make sure it is large enough to fit `right_y_axis_name`
    bottom_margin: int
        default: 70; size of the bottom margin in pixels,
        make sure it is large enough to fit value labels
    top_margin: int
        default: 80; size of the top margin in pixels
    height: int, optional
        default: 800; height of the graph in pixels.
        This largest non-outlier value from `data` and `right_data`
        will take the full height

    """
    graph_width = max(
        sum(map(lambda graph_value: graph_value.x_step, data)),
        0
        if right_data is None
        else sum(map(lambda graph_value: graph_value.x_step, right_data)),
    )
    width = graph_width + left_margin + right_margin
    zero_line = top_margin + height

    img = Image.new(
        "RGB", (width, height + bottom_margin + top_margin), (255, 255, 255)
    )
    draw = ImageDraw.Draw(img)

    if right_data is not None:
        for pil_data in _render_data(
            right_data, height, x0=left_margin + 1, y0=zero_line, spacing=right_spacing
        ):
            pil_data.draw(img, draw, (170, 170, 170))

    _annotate_y_axes(
        draw,
        _data_max(data),
        y_axis_name,
        width,
        height,
        zero_line,
        right_maximum=None if right_data is None else _data_max(right_data),
        right_axis_name=right_y_axis_name,
        ticks=ticks,
    )

    for pil_data in _render_data(
        data, height, x0=left_margin + 1, y0=zero_line, spacing=spacing
    ):
        pil_data.draw(img, draw)

    # title
    draw_label(
        x=left_margin + (graph_width // 2), y=2, img=img, label=title, anchor="tc"
    )

    img.save(output_name, format="png")


def _render_data(
    data: Graph_data, height: int, x0: int, y0: int, spacing: int
) -> Iterator[PilData]:
    """Transorms graph_values in `data` to `PilData`
    and yields them."""
    maximum = _data_max(data)
    x = x0

    for w, h, label, outlier in data:
        pil_data: PilData = PilData()

        value = height if outlier else round((h * height / maximum))
        pil_data.rectangle = [(x, y0), (x + w - 1, y0 - value)]
        pil_data.x_label = label

        x += w + spacing

        if outlier:
            pil_data.y_label = "{:_}".format(h)
            pil_data.outlier = True
        else:
            pil_data.outlier = False

        yield pil_data


def _data_max(data: Graph_data) -> int:
    if len(data) == 0:
        return 0
    
    return max(
        map(
            lambda graph_value: graph_value.value,
            filter(lambda graph_value: not graph_value.outlier, data),
        )
    )


def _annotate_y_axes(
    draw: ImageDraw.ImageDraw,
    maximum: int,
    axis_name: str,
    width: int,
    height: int,
    y0: int,
    right_maximum: Optional[int] = None,
    right_axis_name: Optional[int] = None,
    ticks: Optional[int] = 5,
    font: ImageFont.ImageFont = None,
):
    # y axis names
    _, text_height = get_text_size(axis_name)
    draw.text((2, y0 + text_height + 6), axis_name, fill=(0, 0, 0))

    if right_axis_name is not None:
        text_width, text_height = get_text_size(right_axis_name)
        draw.text(
            (width - 2 - text_width, y0 + text_height + 6),
            right_axis_name,
            fill=(0, 0, 0),
        )

    # y tick values
    if ticks <= 0:
        return

    step = height // ticks
    y = y0

    for i in range(ticks + 1):
        draw.text((2, y), "{:_}".format(maximum // ticks * i), fill=(0, 0, 0))

        if right_maximum is not None:
            text_width, _ = get_text_size(
                "{:_}".format(right_maximum // ticks * i), font
            )
            draw.text(
                (width - 2 - text_width, y),
                "{:_}".format(right_maximum // ticks * i),
                fill=(0, 0, 0),
            )

        draw.rectangle([(2, y), (width - 2, y)], fill=(100, 100, 100))
        y -= step
