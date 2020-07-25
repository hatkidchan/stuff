#!/usr/bin/python3
from PIL import Image
from sys import argv
import os
from math import log, ceil

# termsize = (160, 160)
# termsize = tuple(map(int, os.popen('stty size', 'r').read().split()[::-1]))
termsize = (160, 160)
# termsize = termsize[0], termsize[1] - 4
is_colored = False
is_truecolor = False
color_bg = False
color_fg = True
is_round = False
mapping = ' ._=*^"13%&@$#'
# mapping = [' '] + ['▬'] * 4
# mapping = [' '] + ['\u2593'] * 3
# mapping = '\u2591\u2592\u2593\u2588'
# mapping = '\u2588'
# mapping = ''
# mapping = '01'
# mapping = '.#'
# mapping = list(reversed(mapping))




def rgb2vt100(r, g, b):
    vr, vg, vb = r // 42, g // 42, b // 42
    if is_round:
        vr = (vr // 2) * 2
        vg = (vg // 2) * 2
        vb = (vb // 2) * 2
    return 16 + vr * 36 + vg * 6 + vb


max_rgb2 = ((256 ** 2) * 3) ** 0.5
def process_frame(frame, out_name, width, height, color=True):
    if color:
        frame = frame.convert('RGB')
    else:
        frame = frame.convert('L')
    frame = frame.resize((width, height))
    data = frame.getdata()
    old_c = None
    with open(out_name, 'w') as f:
        for y in range(height):
            for x in range(width):
                val = data[x + y * width]
                if color:
                    r, g, b = val
                    val = ((r ** 2 + g ** 2 + b ** 2) ** 0.5) / max_rgb2
                    if not is_truecolor:
                        vtc = rgb2vt100(r, g, b)
                else:
                    val = val / 256
                sym = mapping[int(val * len(mapping))]
                if color:
                    if is_truecolor:
                        if color_fg:
                            f.write(f'\x1b[38;2;{r};{g};{b}m')
                        if color_bg:
                            f.write(f'\x1b[48;2;{r};{g};{b}m')
                    elif old_c != vtc:
                        f.write(f'\x1b[38;5;{vtc}m')
                        old_c = vtc
                f.write(sym)
            f.write('\n')
            if is_truecolor and color:
                f.write('\x1b[0m')
        if color:
            f.write('\x1b[0m')

argc = len(argv) - 1
for ii, filename in enumerate(argv[1:]):
    im = Image.open(filename)
    basename = os.path.splitext(filename)[0]

    width, height = im.width, im.height // 2
    scale = min(termsize[0] / width, termsize[1] / height)
    width = int(width * scale)
    height = int(height * scale)


    if not getattr(im, 'is_animated', False):
        process_frame(im, basename + '.txt', width, height, is_colored)
        bar = '[%-30s]' % ('=' * int(30 * (ii + 1) / argc))
        print(f"\r\x1b[C{filename} {bar} {ii + 1:5d}/{argc:5d}", end='', flush=1)
    else:
        count = im.n_frames
        name_format = '%s-%%0%dd.txt' % (basename, ceil(log(count, 10) + 1))
        for i in range(count):
            im.seek(i)
            process_frame(im, name_format % i, width, height, is_colored)
            print('\r\x1b[C' + (name_format % i) + '[%-30s] %3d/%3d' % (
                '=' * int(30 * (i + 1) / count),
                i + 1, count
            ), end='', flush=1)
        print()
