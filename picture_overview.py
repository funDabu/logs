from log_stats import Log_stats
from PIL import Image, ImageDraw, ImageFont
from typing import List, Optional
import sys


MONTHS = ["Error", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def make_annotations(maximum: int) -> List[str]:
    fifth = maximum // 5
    return [ "{:.2e}".format(fifth * i) for i in range(6) ]


def annotate(draw: ImageDraw, annotations: List[str], width:int, height: int, top_margin: int):
    fifth = height // 5
    y = height + top_margin

    for i in range(6):
        draw.text( (2, y), annotations[i], fill=(0,0,0) )
        draw.rectangle( [(2, y), (width, y) ], fill=(180,180,180) )
        y -= fifth
    

def print_month(x: int, height: int, month: str, img: Image.Image):
    font = ImageFont.load_default()

    # older version
    # w, h = font.getsize(month)

    # new version 
    l, t, r, b = font.getbbox(month)
    w = r-l
    h = b-t

    month_img = Image.new('L', (w,h), 'white')
    month_draw = ImageDraw.Draw(month_img)
    month_draw.text((0,0), month, fill=0)

    month_img = month_img.rotate(90, expand=1)
    img.paste(month_img, (x, height))

def make_picture(stats: Optional[Log_stats] = None,
                 output_name: str = "overview.png"):
    if stats is None:
        stats = Log_stats(sys.stdin, True)
    data = sorted(stats.daily_data.items(), key=lambda x: x[0])
    # values = list( map(lambda x: x[1][1], data) ) # just request numbers

    # print(data)

    maximum = max(map(lambda x: x[1][1], data))
    annotations = make_annotations(maximum)
    # print(annotations)
    left_margin = 60
    bottom_margin = 70
    top_margin = 10
    height = 800
    width = 2*len(data) + left_margin

    # print("\n", "width:", width)

    img = Image.new('RGB', (width, height + bottom_margin + top_margin), 'white')
    draw = ImageDraw.Draw(img)
    annotate(draw, annotations, width, height, top_margin)
    current_month = None

    for x, (date, (_, value)) in enumerate(data):
        x = x*2 + left_margin
        value = round((value / maximum) * height)
        draw.rectangle([(x, height + top_margin), (x+1 , height-value+top_margin)],
                       fill=(0,0,0) )
        
        month = f"{MONTHS[date.month]} {date.year}"
        if month != current_month:
            current_month = month
            print_month(x, height + 4 + top_margin, month, img)

    img.save(output_name, format="png")


def main():
    make_picture()


if __name__ == '__main__':
    main()