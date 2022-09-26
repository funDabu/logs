from __future__ import annotations
from log_stats import Log_stats
from PIL import Image, ImageDraw
from typing import List
import sys


def make_annotations(maximum: int) -> List[str]:
    fifth = maximum // 5
    return [ "{:.2e}".format(fifth * i) for i in range(6) ]


def annotate(draw: ImageDraw, annotations: List[str], width:int, height: int, margin: int):
    fifth = height // 5
    y = height
    for i in range(0, 6):
        draw.text((0, y), annotations[i], fill=(0,0,0))
        y -= fifth

        draw.rectangle([(0, y), (width, y+1)], fill=(200,200,200))


def make_picture():
    stats = Log_stats(sys.stdin, True)
    data = sorted(stats.daily_data.items(), key=lambda x: x[0])
    data = list( map(lambda x: x[1][1], data) ) # just request numbers

    # print(data)

    maximum = max(data)
    annotations = make_annotations(maximum)
    print(annotations)
    margin = 60
    height = 800
    width = 2*len(data) + margin

    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    annotate(draw, annotations, width, height, margin)

    for x, value in enumerate(data):
        x = x*2 + margin
        value = round((value / maximum) * height)
        draw.rectangle([(x, height), (x+1 , height-value)],
                       fill=(0,0,0) )


    
    img.save("../overview.png", format="png")


def main():
    make_picture()


if __name__ == '__main__':
    main()