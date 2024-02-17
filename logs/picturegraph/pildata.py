from logs.picturegraph.helpers import draw_label
from PIL import Image, ImageDraw


class PIL_data:
    """Data structure to strore rendered grapt value"""
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
             color=(0, 0, 0)):
        rec = self.rectangle
        draw.rectangle(rec, fill=color)

        draw_label(rec[0][0], rec[0][1] + 2,
                    img, self.x_label,
                    rotation=90, anchor="tl")
        
        if self.outlier:
            overstep = 2
            height = 5
            b1 = (rec[0][0] - overstep, rec[1][1] - 1)
            b2 = (rec[1][0] + overstep, rec[1][1] - 1)

            v = ((rec[0][0] + rec[1][0]) // 2, rec[1][1] - height - 1)

            draw.polygon([b1, b2, v], fill=(0, 0, 0))
            draw_label(v[0], v[1]-2, img, self.y_label, 90, "bc")
