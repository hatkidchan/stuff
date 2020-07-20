#!/usr/bin/env python3
# Usage: python3 $0 input-frames/frame* output-folder
# Example:
"""
mkdir frames-{in,out}
ffmpeg -i source.mp4 frames-in/f%4d.png
python3 video-rgb-delay.py frames-in/f*.png frames-out
ffmpeg -r 30 -i frames-out/frame%5d.png -pix_fmt yuv420p -c:v libx264 -profile:v baseline output.mp4
"""
from PIL import Image
from sys import argv
from math import log
from os.path import join
from time import time

_, *in_files, out_folder = argv

size = Image.open(in_files[0]).size
stack = [
    Image.new('RGB', size, 0) for _ in range(3)
]

# name_format = 'frame%%0%dd' % int(log(len(in_files), 10) + 1)
name_format = 'frame%05d'
count = len(in_files)
start_ts = time()

for i, name in enumerate(in_files, 1):
    stack.append(Image.open(name).convert('RGB'))
    stack.pop(0)
    r_im = stack[2].split()[0]
    g_im = stack[1].split()[1]
    b_im = stack[0].split()[2]
    out = Image.merge('RGB', (r_im, g_im, b_im))
    out_name = join(out_folder, name_format % i) + '.png'
    out.save(out_name)
    print('\r[%4d/%4d|%7.2fFPS|%7.3f%%|%-40s]' % (
        i, count, i / (time() - start_ts),
        i * 100 / count,
        '=' * int(i * 40 / count),
    ), end='', flush=1)

print()
