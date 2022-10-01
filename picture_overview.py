from log_stats import Log_stats, Stat_struct
from PIL import Image, ImageDraw, ImageFont
from typing import Callable, List, Optional, Tuple, Iterable
import sys


MONTHS = ["Error", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def make_annotations(maximum: int) -> List[str]:
    # Currently not used
    fifth = maximum // 5
    return [ "{:.2e}".format(fifth * i) for i in range(6) ]


def annotate(draw: ImageDraw.ImageDraw,
             day_maximum: int,
             month_maximum: int,
             width:int,
             height: int,
             zero_line: int,
             font: ImageFont.ImageFont=None):
    fifth = height // 5
    y = zero_line
    label_width, _ = get_text_size("{:.2e}".format(day_maximum), font)

    for i in range(6):
        draw.text((2, y), "{:.2e}".format( day_maximum // 5 * i), fill=(0,0,0))
        draw.text((width-2-label_width, y),
                  "{:.2e}".format( month_maximum // 5 * i),
                  fill=(0,0,0))
        draw.rectangle( [(2, y), (width-2, y) ], fill=(100,100,100) )
        y -= fifth


def get_text_size(text: str, font: Optional[ImageFont.ImageFont] = None) -> int:
    if font is None:
        font = ImageFont.load_default()
    
    # older version - will be removed in Pillow 10 (2023)
    w, h = font.getsize(text)

    # # new version 
    # l, t, r, b = font.getbbox(text)
    # w = r-l
    # h = b-t

    return (w, h)


def print_month(x: int, zero_line: int, month: str, img: Image.Image):
    w,h = get_text_size(month)
    month_img = Image.new('L', (w,h), 'white')
    month_draw = ImageDraw.Draw(month_img)
    month_draw.text((0,0), month, fill=0)

    month_img = month_img.rotate(90, expand=1)
    img.paste(month_img, (x, zero_line + 2))


def get_months_maximum(stat: Log_stats):
    # Currently not used

    def get_max_month_reqs(struct: Stat_struct) -> int:
        max1 = max( struct.month_req_distrib.values() )
        # print(max1) #DEBUG
        return max1

    maxs = map(lambda x: get_max_month_reqs(x[0]) + get_max_month_reqs(x[1]),
               stat.year_stats.values() )
    
    return max(maxs)


def day_data_to_month_data(data:Iterable[Tuple[int, int, str]])\
                            -> List[Tuple[int, int, str]]:
    month_data = []

    current_month = None
    month_value = 0
    month_width = 0

    for width, value, date in data:
        split_date = date.split("-") # date is isoformat ("YYYY-MM-DD")
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
    

def make_both_pictures(stats: Log_stats):
    base_step = 2

    data = sorted(stats.daily_data.items(), key=lambda x: x[0])
    # print(data) #DEBUG

    # pure request count
    day_data = list(map(lambda x: (base_step, x[1][1], x[0].isoformat()), data))
    # DEBUG ^make it more readabel 
    # print(day_data) #DEBUG
    month_data = day_data_to_month_data(day_data)
    make_picture(day_data, month_data, base_step, "requests_overview.png")

    # unique IP count
    day_data = list(map(lambda x: (base_step, len(x[1][0]), x[0].isoformat()), data))
    month_data = day_data_to_month_data(day_data)
    make_picture(day_data, month_data, base_step, "unique_ip_overview.png")
     

def fix_outliers(month_data: List[Tuple[int, int, str]])\
        -> int:
    pass

def make_picture(day_data: List[Tuple[int, int, str]],
                 month_data: List[Tuple[int, int, str]],
                 base_step: int,
                 output_name: str = "overview.png"):

    day_maximum = max(map(lambda x: x[1], day_data))
    month_maximum = max(map(lambda x: x[1], month_data))
    # print(months_maximum) # DEBUG

    left_margin = 60
    right_margin = 60
    bottom_margin = 70
    top_margin = 10
    height = 800
    width = base_step*len(day_data) + left_margin + right_margin

    zero_line = top_margin + height

    day_recs = get_rectangles(day_data, day_maximum, height, left_margin, zero_line)
    month_recs = get_rectangles(month_data, month_maximum, height, left_margin, zero_line)

    img = Image.new('RGB', (width, height + bottom_margin + top_margin), (255,255,255))
    draw = ImageDraw.Draw(img)

    for coords, _ in month_recs:
        draw.rectangle(coords, fill=(150,150,150))
    annotate(draw, day_maximum, month_maximum, width, height, zero_line)
    for coords,_ in day_recs:
        draw.rectangle(coords, fill=(0,0,0))
    draw_x_labels(img, month_recs, zero_line, pritify_month)

    img.save(output_name, format="png")


def get_rectangles(data: Iterable[Tuple[int, int, str]],
                   maximum: int,
                   height: int,
                   x: int,
                   zero_line: int)\
    -> List[Tuple[ Tuple[Tuple[int, int],Tuple[int,int]], str]]:

    rectangles = []

    for w, h, label in data:
        value = round((h * height / maximum))
        rectangles.append(([(x, zero_line), (x+w-1 , zero_line-value)], label))
        x += w
 
    return rectangles


def pritify_month(month: str) -> str:
    splited_month = month.split("-")
    pretty_month = MONTHS[int(splited_month[1])]
    return f"{pretty_month} {splited_month[0]}"


def draw_x_labels(img: Image.Image,
                  rectangles: List[Tuple[ Tuple[Tuple[int, int],
                                                Tuple[int,int]],
                                          str ]],
                  zero_line: int,
                  pritify: Callable[[str], str] = lambda x:x):
    for coords, label in rectangles:
        x = coords[0][0]
        zero_line = coords[0][1]
        print_month(x, zero_line, pritify(label), img)


def main():
    stats = Log_stats(sys.stdin, True)
    make_both_pictures(stats)


if __name__ == '__main__':
    main()