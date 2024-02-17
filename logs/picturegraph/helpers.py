from PIL import Image, ImageDraw, ImageFont
from typing import Optional


def draw_label(x: int,
               y: int,
               img: Image.Image,
               label: str,
               rotation: int = 0,
               anchor: str = "tl"):
    """anchor: "[tcb][lcr]" """

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


def get_text_size(text: str,
                  font: Optional[ImageFont.ImageFont] = None)\
        -> int:
    if font is None:
        font = ImageFont.load_default()

    # older version - will be removed in Pillow 10
    w, h = font.getsize(text)

    # # new version
    # l, t, r, b = font.getbbox(text)
    # w = r-l
    # h = b-t

    return (w, h)