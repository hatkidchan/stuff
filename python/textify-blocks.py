#!/usr/bin/env python3
from PIL import Image
from sys import argv, stdout


# Enable truecolor
TRUECOLOR = True

# maximum colors per channel
TRUECOLOR_GRADES = 128

# from 0 to (256 ** 3), values above 32 are NOT recommended
TRUECOLOR_SAME_THRESHOLD = 10

# values bellow are transparen. tnot implemented yet.
ALPHA_THRESHOLD = 50


BLOCK_HALF_LOWER = '\u2584'
BLOCK_HALF_UPPER = '\u2580'
BLOCK_FULL = '\u2588'

VT100_ALL = '\x1b[38;5;%dm\x1b[48;5;%dm'
VT100_FG = '\x1b[38;5;%dm'
VT100_BG = '\x1b[48;5;%dm'
TCOLOR_FG = '\x1b[38;2;%d;%d;%dm'
TCOLOR_BG = '\x1b[48;2;%d;%d;%dm'


def rgb2vt100(r, g, b):
    vr, vg, vb = r // 42, g // 42, b // 42
    return 16 + vr * 36 + vg * 6 + vb


def round_color(rgb, grades=256):
    return tuple([int(int(v / (256 / grades)) * (256 / grades))
                  for v in rgb])


def color_dist(rgb1, rgb2):
    # linear looks awful, sooo, yeah...
    return sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)) ** 0.5


def is_same(a, b, t):
    if a is None or b is None:
        return False
    return color_dist(a, b) < t


def convert(input_image, output_fp, truecolor=False, tc_grades=256, tc_same=1):
    for y in range(0, (input_image.height // 2) * 2, 2):
        old_fg, old_bg = None, None
        for x in range(input_image.width):
            *clr_u, al_u = input_image.getpixel((x, y))
            *clr_d, al_d = input_image.getpixel((x, y + 1))
            clr_u = round_color(clr_u, tc_grades)
            clr_d = round_color(clr_d, tc_grades)
            pal_u = rgb2vt100(*clr_u)
            pal_d = rgb2vt100(*clr_d)
            if truecolor:
                if not is_same(clr_u, old_fg, tc_same):
                    old_fg = clr_u
                    output_fp.write(TCOLOR_FG % tuple(clr_u))
                if not is_same(clr_d, old_bg, tc_same):
                    old_bg = clr_d
                    output_fp.write(TCOLOR_BG % tuple(clr_d))
                if clr_d != clr_u:
                    output_fp.write(BLOCK_HALF_UPPER)
                else:
                    output_fp.write(BLOCK_FULL)
            else:
                if pal_u != old_fg:
                    old_fg = pal_u
                    output_fp.write(VT100_FG % pal_u)
                if pal_d != old_bg:
                    old_bg = pal_d
                    output_fp.write(VT100_BG % pal_d)
                if pal_d == pal_u:
                    output_fp.write(BLOCK_FULL)
                else:
                    output_fp.write(BLOCK_HALF_UPPER)
        output_fp.write('\x1b[0m\n')


with Image.open(argv[1]) as img:
    img.thumbnail((160, 100))
    img = img.convert('RGBA')
    with open(argv[1] + '.txt', 'w') as fp:
        convert(img, fp, TRUECOLOR, TRUECOLOR_GRADES, TRUECOLOR_SAME_THRESHOLD)

