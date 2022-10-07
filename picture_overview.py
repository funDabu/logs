from log_stats import Log_stats
from PIL import Image, ImageDraw, ImageFont
from typing import Iterator, List, Optional, Tuple, Iterable, Union
import sys
import json


MONTHS = ["Error", "Jan", "Feb", "Mar", "Apr", "May",
          "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def annotate(draw: ImageDraw.ImageDraw,
             day_maximum: int,
             month_maximum: int,
             width: int,
             height: int,
             zero_line: int,
             font: ImageFont.ImageFont = None):
    fifth = height // 5
    y = zero_line

    for i in range(6):
        draw.text((2, y),
                   "{:_}".format(day_maximum // 5 * i),
                   fill=(0, 0, 0))

        text_width, _ = get_text_size("{:_}".format(
                month_maximum // 5 * i), font)                       
        draw.text((width-2-text_width, y),
                  "{:_}".format(month_maximum // 5 * i),
                  fill=(0, 0, 0))

        draw.rectangle([(2, y), (width-2, y)], fill=(100, 100, 100))
        y -= fifth

    # y axis names
    _, text_height = get_text_size("per day")
    draw.text((2, zero_line + text_height + 6), "per day", fill=(0, 0, 0))

    text_width, text_height = get_text_size("per month")
    draw.text((width-2-text_width, zero_line + text_height + 6),
              "per month", fill=(0, 0, 0))


def get_text_size(text: str,
                  font: Optional[ImageFont.ImageFont] = None)\
        -> int:
    if font is None:
        font = ImageFont.load_default()

    # older version - will be removed in Pillow 10 (2023)
    w, h = font.getsize(text)

    # # new version
    # l, t, r, b = font.getbbox(text)
    # w = r-l
    # h = b-t

    return (w, h)


def draw_label(x: int,
               y: int,
               img: Image.Image,
               label: str,
               rotation: int = 0,
               anchor: str = "tl"):
    # anchor: "[tcb][lcr]"

    w, h = get_text_size(label)
    label_img = Image.new('L', (w, h), 255)
    label_draw = ImageDraw.Draw(label_img)
    label_draw.text((0, 0), label, fill=0)

    if rotation:
        label_img = label_img.rotate(rotation, expand=1)

    pic_w, pic_h = label_img.size
    if anchor[0] == "b":
        y -= pic_h
    elif anchor[0] == "c":
        y -= pic_h // 2
    if anchor[1] == "r":
        x -= pic_w
    elif anchor[1] == "c":
        x -= pic_w // 2

    img.paste(label_img, (x, y))


def day_data_to_month_data(data: Iterable[Tuple[int, int, str]])\
        -> List[Tuple[int, int, str]]:
    month_data = []

    current_month = None
    month_value = 0
    month_width = 0

    for width, value, date in data:
        split_date = date.split("-")  # date is isoformat ("YYYY-MM-DD")
        month = f"{split_date[0]}-{split_date[1]}"

        if month != current_month:
            if current_month is not None:
                month_data.append((month_width, month_value, current_month))
                month_value, month_width = 0, 0
            current_month = month

        month_width += width
        month_value += value

    month_data.append((month_width, month_value, current_month))
    return month_data


def make_both_pictures(stats: Union[Log_stats, str], load_json=False, output_json=""):
    base_step = 2

    if load_json:
        with open(stats, "r") as data_f:
            data = json.load(data_f)
    else:
        # make data form stats: Log_stats
        data_objects = sorted(stats.daily_data.items(), key=lambda x: x[0])
        data = {}

        # pure request count
        data["day_requests"] = list(
            map(lambda x: (base_step, x[1][1], x[0].isoformat()), data_objects))
        # DEBUG ^make it more readabel
        # print(data["day_requests"]) #DEBUG
        data["month_requests"] = day_data_to_month_data(data["day_requests"])

        # unique IP count
        data["day_ips"] = list(
            map(lambda x: (base_step, len(x[1][0]), x[0].isoformat()), data_objects))
        data["month_ips"] = day_data_to_month_data(data["day_ips"])

    # print(data) #DEBUG

    if output_json != "":
        with open(output_json, "w") as output_f:
            json.dump(data, output_f)

    make_picture(data["day_requests"], data["month_requests"],
                 base_step, True, "requests_overview.png")
    make_picture(data["day_ips"], data["month_ips"],
                 base_step, False, "unique_ip_overview.png")


def get_day_max(day_data: List[Tuple[int, int, str]],
                month_count: int, fix_outlieres=False)\
        -> int:
    # fix outliers

    count = month_count // 4 if fix_outlieres else 0  # 3 possible outliers per year
    day_maxs = sorted(map(lambda x: x[1], day_data), reverse=True)[:count+1]
    return day_maxs[-1]


def make_picture(day_data: List[Tuple[int, int, str]],
                 month_data: List[Tuple[int, int, str]],
                 base_step: int,
                 fix_outlieres: bool = False,
                 output_name: str = "overview.png"):

    day_maximum = get_day_max(day_data, len(month_data), fix_outlieres)
    month_maximum = max(map(lambda x: x[1], month_data))
    # print(months_maximum) # DEBUG

    left_margin = 70
    right_margin = 70
    bottom_margin = 70
    top_margin = 80
    height = 800
    width = base_step*len(day_data) + left_margin + right_margin

    zero_line = top_margin + height

    img = Image.new('RGB', (width, height + bottom_margin +
                    top_margin), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    for data_object in render_iter(month_data,
                                   month_maximum,
                                   height,
                                   left_margin + 1,
                                   zero_line,
                                   False):
        data_object.draw(img, draw, (170, 170, 170), True, pritify_month)

    annotate(draw, day_maximum, month_maximum, width, height, zero_line)
    for data_object in render_iter(day_data,
                                   day_maximum,
                                   height,
                                   left_margin + 1,
                                   zero_line,
                                   fix_outlieres):
        data_object.draw(img, draw)

    img.save(output_name, format="png")


class PIL_data:
    __slots__ = ("rectangle", "arrow", "x_label", "y_label", "outlier")

    def __init__(self, outlier=False) -> None:
        self.rectangle = []
        self.arrow = []
        self.x_label = ""
        self.y_label = ""
        self.outlier = outlier

    def draw(self,
             img: Image.Image,
             draw: ImageDraw.ImageDraw,
             color=(0, 0, 0),
             draw_x_labels: bool = False,
             pritify_label=lambda x: x):
        rec = self.rectangle
        draw.rectangle(rec, fill=color)

        if draw_x_labels:
            draw_label(rec[0][0], rec[0][1] + 2,
                       img, pritify_label(self.x_label),
                       rotation=90, anchor="tl")
        if self.outlier:
            overhang = 2
            height = 5
            b1 = (rec[0][0] - overhang, rec[1][1] - 1)
            b2 = (rec[1][0] + overhang, rec[1][1] - 1)

            v = ((rec[0][0] + rec[1][0]) // 2, rec[1][1] - height - 1)

            draw.polygon([b1, b2, v], fill=(0, 0, 0))
            draw_label(v[0], v[1]-2, img, self.y_label, 90, "bc")


def render_iter(data: Iterable[Tuple[int, int, str]],
                maximum: int,
                height: int,
                x: int,
                zero_line: int,
                check_outliers: bool = False)\
        -> Iterator[PIL_data]:
    data_obj: PIL_data = PIL_data()

    for w, h, label in data:
        outlier = check_outliers and h > maximum
        value = height if outlier else round((h * height / maximum))

        data_obj.rectangle = [(x, zero_line), (x+w-1, zero_line - value)]
        x += w
        data_obj.x_label = label
        if outlier:
            data_obj.y_label = "{:_}".format(h)
            data_obj.outlier = True
        else:
            data_obj.outlier = False

        yield data_obj


def pritify_month(month: str) -> str:
    splited_month = month.split("-")
    pretty_month = MONTHS[int(splited_month[1])]
    return f"{pretty_month} {splited_month[0]}"


def main():
    if len(sys.argv) == 3:
        if sys.argv[1] == "load":
            make_both_pictures(sys.argv[2], True)
        elif sys.argv[1] == "save":
            stats = Log_stats(sys.stdin, True)
            make_both_pictures(stats, False, sys.argv[2])
    else:
        stats = Log_stats(sys.stdin, True)
        make_both_pictures(stats)


if __name__ == '__main__':
    main()
