#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont, ImageChops
import sys
import time

font = ImageFont.load_default()
CHARS = ''.join(map(chr, range(32, 127)))
#CHARS = (' !"#$%&\'()*+,-./0123456789:;<=>?'
#         '@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`'
#         'abcdefghijklmnopqrstuvwxyz{|}~¡¢£¤'
#         '¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿'
#         'ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ')
BLOCKSIZE = font.getsize(' ')

PROBE_BLOCKS = {}

timers = {}

def clock(name):
    if name not in timers:
        timers[name] = {'calls': 0, 'time': 0}
    def decorator(func):
        def wrapped(*p, **k):
            s = time.time()
            d = func(*p, **k)
            timers[name]['time'] += (time.time() - s)
            timers[name]['calls'] += 1
            return d
        return wrapped
    return decorator 


@clock('make')
def make_block(char):
    im = Image.new('L', BLOCKSIZE)
    ImageDraw.Draw(im).text((0, 0), char, font=font, fill=255)
    return im

@clock('probe')
def probe_char(img, cox, coy):
    sx = BLOCKSIZE[0] * cox
    sy = BLOCKSIZE[1] * coy
    ex = BLOCKSIZE[0] + sx
    ey = BLOCKSIZE[1] + sy
    
    area = clock('crop')(img.crop)((sx, sy, ex, ey))
#    print(area.size)
    maxdiff = BLOCKSIZE[0] * BLOCKSIZE[1] * 255
    best = maxdiff, '?'
    for char, probe in PROBE_BLOCKS.items():
        diff = clock('diff')(ImageChops.difference)(area, probe)
        diff_int = clock('sum')(sum)(clock('get')(diff.getdata)())
        if diff_int < best[0]:
            best = diff_int, char
    return best[1]

for c in CHARS:
    PROBE_BLOCKS[c] = make_block(c)

image = Image.open(sys.argv[1]).convert('L')
image.thumbnail((320 * BLOCKSIZE[0], 100 * BLOCKSIZE[1]))

orig_size = image.size
blocks = [a // b for a, b in zip(orig_size, BLOCKSIZE)]

if True:
    # out = ''
    for y in range(blocks[1]):
        # line = ''
        for x in range(blocks[0]):
            char = probe_char(image, x, y)
            # line += char
            print(char, end='', flush=1)
        print()
        # out += line + '\n'
        # print(line)
# char = probe_char(image, blocks[0]-1, blocks[1]-1)
# print(char)

# for k in sorted(timers, key=lambda k: timers[k]['time']):
#     print(k, timers[k]['time'])
