from log_stats import Log_stats
from PIL import Image
import sys


def fill_rectangle(pixels, x_orig, y_orig, x_length, y_length, color):
    for x in range(x_length):
        for y in range(y_length):
            pixels[x_orig + x, y_orig + y] = color


def make_picture():
    stats = Log_stats(sys.stdin, True)
    
    data = sorted(stats.daily_data.items(), key=lambda x: x[0])
    data = list( map(lambda x: x[1][1], data) ) # just request numbers
    img = Image.new('RGB', (len(data)*2, max(data) + 10), 'white')

    pixels = img.load()
    color = (0, 0, 0)


    print("here")
    for x, req_num in enumerate(data):
        fill_rectangle(pixels,
                       x*2, 0,
                       2, req_num,
                       color)
    
    img.show()


def main():
    make_picture()


if __name__ == '__main__':
    main()