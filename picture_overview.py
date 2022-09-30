from log_stats import Log_stats, Stat_struct
from PIL import Image, ImageDraw, ImageFont
from typing import List, Optional
import sys


MONTHS = ["Error", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def make_annotations(maximum: int) -> List[str]:
    fifth = maximum // 5
    return [ "{:.2e}".format(fifth * i) for i in range(6) ]


def annotate(draw: ImageDraw,
             day_annotations: List[str],
             month_annotations: List[str],
             width:int, height: int,
             zero_line: int):
    fifth = height // 5
    y = zero_line

    month_width, _ = get_text_size(month_annotations[-1])

    for i in range(6):
        draw.text((2, y), day_annotations[i], fill=(0,0,0))
        draw.text((width - month_width - 2, y),
                  month_annotations[i],
                  fill=(0,0,0) )
        draw.rectangle( [(2, y), (width-2, y) ], fill=(100,100,100) )
        y -= fifth


def get_text_size(text: str, font: Optional[ImageFont.ImageFont] = None) -> int:
    if font is None:
        font = ImageFont.load_default()
    
    # older version
    # w, h = font.getsize(month)

    # new version 
    l, t, r, b = font.getbbox(text)
    w = r-l
    h = b-t

    return (w, h)


def print_month(x: int, zero_line: int, month: str, img: Image.Image):
    w,h = get_text_size(month)
    month_img = Image.new('L', (w,h), 'white')
    month_draw = ImageDraw.Draw(month_img)
    month_draw.text((0,0), month, fill=0)

    month_img = month_img.rotate(90, expand=1)
    img.paste(month_img, (x, zero_line + 2))


def get_months_maximum(stat: Log_stats):

    def get_max_month_reqs(struct: Stat_struct) -> int:
        max1 = max( struct.month_req_distrib.values() )
        # print(max1) #DEBUG
        return max1

    maxs = map(lambda x: get_max_month_reqs(x[0]) + get_max_month_reqs(x[1]),
               stat.year_stats.values() )
    
    return max(maxs)


def make_picture(stats: Optional[Log_stats] = None,
                 output_name: str = "overview.png"):
    if stats is None:
        stats = Log_stats(sys.stdin, True)
    data = sorted(stats.daily_data.items(), key=lambda x: x[0])
    # print(data) #DEBUG

    maximum = max(map(lambda x: x[1][1], data))
    months_maximum = get_months_maximum(stats)
    # print(months_maximum) # DEBUG
    day_annotations = make_annotations(maximum)
    month_annotaions = make_annotations(months_maximum)

    left_margin = 60
    right_margin = 60
    bottom_margin = 70
    top_margin = 10
    height = 800
    width = 2*len(data) + left_margin + right_margin

    zero_line = top_margin + height


    day_recs, month_recs, x_labels = get_rectangles(data,
                                                    maximum,
                                                    months_maximum,
                                                    height,
                                                    width,
                                                    left_margin,
                                                    right_margin,
                                                    zero_line )
    
    # print("\n", "width:", width)

    img = Image.new('RGB', (width, height + bottom_margin + top_margin), (255,255,255))
    draw = ImageDraw.Draw(img)

    for coords in month_recs:
        draw.rectangle(coords, fill=(120,120,120))
    annotate(draw, day_annotations, month_annotaions, width, height, zero_line)
    for coords in day_recs:
        draw.rectangle(coords, fill=(0,0,0))
    for x, label in x_labels:
        print_month(x, zero_line, label, img)


    # month_img.paste(img)
    img.save(output_name, format="png")


def get_rectangles(data,
                maximum: int, # day maximum
                months_maximum: int,
                height: int,
                width: int,
                left_margin: int,
                right_margin: int,
                zero_line: int ):

    current_month = None
    month_value = 0
    month_start_x = left_margin

    day_rectangles = []
    month_rectangles = []
    x_labels = []

    for x, (date, (_, value)) in enumerate(data):
        x = x*2 + left_margin

        day_value = round((value * height / maximum))
        day_rectangles.append([(x, zero_line), (x+1 , zero_line-day_value)])
        
        month = f"{MONTHS[date.month]} {date.year}"
        if month != current_month:
            # Append month rectangle and x-label
            if current_month is not None:
                month_value = (round(month_value * height/ months_maximum))
                month_rectangles.append([(month_start_x, zero_line),
                                          (x-1, zero_line-month_value)] )
                month_start_x = x
                month_value = 0

            current_month = month 
            x_labels.append((x, month))

        month_value += value
        # print(month) # DEBUG

    # appned last month rectangle
    month_value = (round(month_value * height / months_maximum))
    month_rectangles.append([(month_start_x, zero_line),
                             (width-right_margin, zero_line-month_value)])

    return (day_rectangles, month_rectangles, x_labels)

    
def main():
    make_picture()


if __name__ == '__main__':
    main()