#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont, ImageChops
from flask import Flask, request, Response, stream_with_context
from io import StringIO
from textwrap import dedent
from html import escape


######################################################################
#   CONVERTERS CONSTANT VALUES, DO NOT CHANGE THEM, PLEASE T.T       #
######################################################################
# Generic variables
SEQ_TRUECOLOR_FG = '\x1b[38;2;%d;%d;%dm'
SEQ_TRUECOLOR_BG = '\x1b[48;2;%d;%d;%dm'
SEQ_VT100_FG = '\x1b[38;5;%dm'
SEQ_VT100_BG = '\x1b[48;5;%dm'
HTML_BACKGROUND = '<div style="display:inline-block;background:#%02x%02x%02x">'
HTML_FOREGROUND = '<div style="display:inline-block;color:#%02x%02x%02x">'
HTML_CLOSE = '</div>'
RESULT_MAX_SIZE = 160, 50  # in characters
# True ASCII
TRUEASCII_CHARS = ''.join(chr(c) for c in range(0x20, 0x7f))
TRUEASCII_FONT = ImageFont.load_default()
TRUEASCII_BLOCK_SIZE = TRUEASCII_FONT.getsize(' ')
TRUEASCII_BLOCKS_1 = {}  # will be populated later
TRUEASCII_BLOCKS_L = {}  # will be populated later
# Colorful charmap
COLORFULMAP_DEFAULT_CHARSET = ' ._=*^"13%&@$#'
# Colorful blocks
COLORFULBLK_BLOCK_HALF = '\u2584'
COLORFULBLK_BLOCK_FULL = '\u2588'

######################################################################
#   GENERIC FUNCTIONS, REQUIRED IN MOST CONVERTERS, POORLY DONE      #
######################################################################
def rgb2vt100(r, g, b):
    if r == g and g == b:
        if r < 8:
            return 16
        if r > 248:
            return 231
        return 232 + int(((r - 8) / 247) * 24)
    code = 16
    code += (36 * int(r / 255 * 5))
    code += (6 * int(g / 255 * 5))
    code += int(b / 255 * 5)
    return code

def vt100rgb(r, g, b):
    code = rgb2vt100(r, g, b)
    if code >= 232 and code <= 255:
        v = int(((code - 232) / 24) * 255)
        return v, v, v
    else:
        code -= 16
        b = (code % 6) * 42
        code //= 6
        g = (code % 6) * 42
        code //= 6
        r = (code % 6) * 42
        return r, g, b

def color_distance(rgb1, rgb2):
    return sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)) ** 0.5

def resize_image(image, width, height):
    ratio = min(width / image.width, height / image.height)
    return image.resize((int(image.width * ratio), int(image.height * ratio)))

def bool_(v):
    if str(v).lower() in ['yes', 'true']:
        return True
    if str(v).lower() in ['no', 'false']:
        return False
    return bool(int(v)) if str(v).isnumeric() else bool(v)

######################################################################
#   CONVERTER-SPECIFIC FUNCTIONS, MOSTLY POOR IMPLEMENTATIONS, TOO   #
######################################################################
def trueascii_make_char_image(char, mode='L'):
    im = Image.new(mode, TRUEASCII_BLOCK_SIZE)
    ImageDraw.Draw(im).text((0, 0), char, font=TRUEASCII_FONT, fill=255)
    return im

def trueascii_probe_char(image, cox, coy, charmap=TRUEASCII_CHARS):
    bw, bh = TRUEASCII_BLOCK_SIZE
    sx, sy = cox * bw, coy * bh
    ex, ey = sx + bw, sy + bh
    area = image.crop((sx, sy, ex, ey))
    charset = TRUEASCII_BLOCKS_1 if image.mode == '1' else TRUEASCII_BLOCKS_L
    best_dist, best_char = bw * bh * 255, '?'
    for char in charmap:
        diff_img = ImageChops.difference(area, charset[char])
        diff_value = sum(diff_img.getdata())
        if diff_value < best_dist:
            best_dist, best_char = diff_value, char
    return best_char


app = Flask(__name__)


@app.route('/conv/trueascii', methods=['POST'])
def conv_trueascii():
    if 'image' not in request.files:
        raise KeyError('no image sent')
    bitmap = bool_(request.args.get('bitmap', request.values.get('bitmap')))
    html = bool_(request.args.get('html', request.values.get('html')))
    charmap = set(request.args.get('charmap',
                                   request.values.get('charmap',
                                                      TRUEASCII_CHARS)))
    image = Image.open(request.files['image']).convert('1' if bitmap else 'L')
    image = resize_image(image, 
                         RESULT_MAX_SIZE[0] * TRUEASCII_BLOCK_SIZE[0],
                         RESULT_MAX_SIZE[1] * TRUEASCII_BLOCK_SIZE[1])
    
    rows = image.height // TRUEASCII_BLOCK_SIZE[1]
    cols = image.width // TRUEASCII_BLOCK_SIZE[0]
    
    charmap = list(filter(lambda c: c in TRUEASCII_CHARS, charmap))

    def process():
        if html:
            yield '<pre style="background:#000000;color:#ffffff">'
        for y in range(rows):
            line = ''
            for x in range(cols):
                line += trueascii_probe_char(image, x, y, charmap)
            yield line + '\n'
        if html:
            yield '</pre>'
    response = Response(stream_with_context(process()))
    response.headers['Content-type'] = ('text/html' if html else 'text/plain'
                                        + '; charset=utf-8')
    return response


@app.route('/conv/charmap', methods=['POST'])
def conv_charmap():
    if 'image' not in request.files:
        raise KeyError('no image sent')
    image = Image.open(request.files['image'])
    color = request.args.get('color', request.values.get('color', 'no'))
    html = bool_(request.args.get('html', request.values.get('html')))
    if color not in ['no', '256', 'truecolor']:
        raise KeyError('unknown color mode, supported only no/256/truecolor')
    image = image.convert('L' if color == 'no' else 'RGB')
    charmap = request.args.get('charmap',
                               request.values.get('charmap',
                                                  COLORFULMAP_DEFAULT_CHARSET))
    
    image = resize_image(image, RESULT_MAX_SIZE[0], RESULT_MAX_SIZE[1] * 2)
    image = image.resize((image.width, image.height // 2))
    
    max_rgb = color_distance((0, 0, 0), (256, 256, 256))
    def process():
        if html:
            yield '<pre style="background:#000000;color:#ffffff">'
        for y in range(image.height):
            line = ''
            for x in range(image.width):
                v = image.getpixel((x, y))
                if color == 'no':
                    line += charmap[int(len(charmap) * v / 256)]
                else:
                    p = color_distance(v, (0, 0, 0)) / max_rgb
                    if color == '256':
                        if html:
                            line += HTML_FOREGROUND % vt100rgb(*v)
                        else:
                            line += SEQ_VT100_FG % rgb2vt100(*v)
                    else:
                        if html:
                            line += HTML_FOREGROUND % v
                        else:
                            line += SEQ_TRUECOLOR_FG % v
                    line += charmap[int(len(charmap) * p)]
                    if html:
                        line += HTML_CLOSE
            yield line + '\n' + ('\x1b[0m' if color != 'no' and not html else '')
        if html:
            yield '</pre>'
    response = Response(stream_with_context(process()))
    response.headers['Content-type'] = ('text/html' if html else 'text/plain'
                                        + '; charset=utf-8')
    return response


@app.route('/conv/blocks', methods=['POST'])
def conv_post():
    if 'image' not in request.files:
        raise KeyError('no image sent')
    color = request.args.get('color', request.values.get('color', 'truecolor'))
    html = bool_(request.args.get('html', request.values.get('html')))
    if color not in ['256', 'truecolor']:
        raise KeyError('unknown color mode, supported only 256 or truecolor')

    image = Image.open(request.files['image']).convert('RGB')
    image = resize_image(image, RESULT_MAX_SIZE[0], RESULT_MAX_SIZE[1] * 2)

    def process():
        if html:
            yield '<pre style="background:#000000;color:#ffffff">'
        for y in range(0, image.height, 2):
            line = ''
            for x in range(image.width):
                r1, g1, b1 = image.getpixel((x, y))
                r2, g2, b2 = image.getpixel((x, y + 1))
                if color == '256':
                    if html:
                        r1, g1, b1 = vt100rgb(r1, g1, b1)
                        r2, g2, b2 = vt100rgb(r2, g2, b2)
                        top = HTML_BACKGROUND % (r1, g1, b1)
                        bot = HTML_FOREGROUND % (r2, g2, b2)
                    else:
                        top = SEQ_VT100_BG % rgb2vt100(r1, g1, b1)
                        bot = SEQ_VT100_FG % rgb2vt100(r2, g2, b2)
                else:
                    if html:
                        top = HTML_BACKGROUND % (r1, g1, b1)
                        bot = HTML_FOREGROUND % (r2, g2, b2)
                    else:
                        top = SEQ_TRUECOLOR_BG % (r1, g1, b1)
                        bot = SEQ_TRUECOLOR_FG % (r2, g2, b2)
                if top == bot:
                    line += bot + COLORFULBLK_BLOCK_FULL
                    if html:
                        line += HTML_CLOSE
                else:
                    line += top + bot + COLORFULBLK_BLOCK_HALF
                    if html:
                        line += HTML_CLOSE * 2
            yield line + ('\n' if html else '\x1b[0m\n')
        if html:
            yield '</pre>'
    response = Response(stream_with_context(process()))
    response.headers['Content-type'] = ('text/html' if html else 'text/plain'
                                        + '; charset=utf-8')
    return response


@app.route('/docs')
def docs():
    max_width, max_height = RESULT_MAX_SIZE
    docs_text = f'''
    Shitty docpage about available methods and their parameters
    ======================================================================
    
    /conv/trueascii
        True image to ASCII-art conversion, most accurate yet slowest method.
        Has no color support (yet), uses characters in range 0x20..0x7e

        Parameters:
            charmap: str = [all chars between 0x20 and 0x7e]
                String of ASCII characters, used while searching best fit
                Empty string may result in a lot of questions.
                Characters outside internal list (described above) will be
                dropped away. Duplicates will be removed too. Order does not
                matter, because characters picked by their mask, not index.
            html: bool = false
                Should we output result in html-friendly format or not.
                In this mode not a lot will be affected: just added PRE tag.
        Image must be sent as file with name 'image'.
        Output text resolution may be {max_width}x{max_height} (in characters)
        Result lines are streamed.
    
    /conv/charmap
        Fast and inaccurate brother of /conv/trueascii, has color support
        and can use any characters you want.
        
        Parameters:
            charmap: str = {COLORFULMAP_DEFAULT_CHARSET!r}
                String of any characters, from 'darkest' to 'brightest'.
                Duplicates are not filtered, empty set may result in empty
                image. Characters choosen by their indexes somhow like:
                char = chars[int(value * len(chars))] where 0 <= value < 1
            color: str['no', '256', 'truecolor'] = 'no'
                Describes which color mode will be used.
                When selected anything but 'no', at end of every line
                will be sent color reset sequence. Color is set only for
                foreground, background is never changed.
                If mode is 'no', image will be converted to grayscale
            html: bool = false
                Should we output result in html-friendly format or not.
                Keep in mind, that colors are displayed via DIV tags
                for each character. Yes, that is not efficient, but very
                easy to implement. Anyway, colors will work, hopefully.
        As always, image bust be sent as file with name 'image'.
        Output text resolution may be {max_width}x{max_height} (in characters)
        Result lines are streamed, too.
        
    /conv/blocks
        Sometimes ugly and non-ASCII at all, 'cause uses unicode characters
        for blocks. But have much higher resolution than others.
        This method uses 'half slab' characters with manipulating of
        background and foreground color.
        
        Parameters:
            color: str['256', 'truecolor'] = 'truecolor'
                No comments, just selects palette.
            html: bool = false
                Should we output result in html-friendly format or not.
                Keep in mind, that colors are displayed via DIV tags
                for each character. Yes, that is not efficient, but very
                easy to implement. Anyway, colors will work, hopefully.

        Image bust be sent blah blah blah.
        Output resolution blah {max_width} blah {max_height} in blah.
        Lines are blah blah blah, at end of every line is sent color reset.
    
    /docs
    /help
        This documentation page.
        
    /ui.html
        Simple set of forms for testig
        
    '''
    def process():
        for line in dedent(docs_text).split('\n'):
            yield line + '\n'
    response = Response(stream_with_context(process()))
    response.headers['Content-type'] = 'text/plain'
    return response


@app.route('/ui.html')
def ui_html():
    return dedent(f'''
    <!DOCTYPE html>
    <html>
        <head>
            <title>Example</title>
            <style>
                body \x7b
                    filter: invert();
                    background: #000000;
                    color: #000000;
                \x7d
            </style>
        </head>
        <body>
            <h1>/conv/trueascii</h1>
            <form action='conv/trueascii' method='POST' enctype='multipart/form-data'>
                <input type='file' name='image'>
                <label for='bitmap'>Bitmap</label><input type='checkbox' name='bitmap'>
                <label for='html'>HTML</label><input type='checkbox' name='html'>
                <input type='text' name='charmap' value="{escape(TRUEASCII_CHARS)}">
                <button type='submit'>Just do it</button>
            </form>
            <h1>/conv/charmap</h1>
            <form action='conv/charmap' method='POST' enctype='multipart/form-data'>
                <input type='file' name='image'>
                <input type='text' name='charmap' value="{escape(COLORFULMAP_DEFAULT_CHARSET)}">
                <label for='html'>HTML</label><input type='checkbox' name='html'>
                <select name='color'>
                    <option>no</option>
                    <option>256</option>
                    <option>truecolor</option>
                </select>
                <button type='submit'>Just do it</button>
            </form>
            <h1>/conv/blocks</h1>
            <form action='conv/blocks' method='POST' enctype='multipart/form-data'>
                <input type='file' name='image'>
                <label for='html'>HTML</label><input type='checkbox' name='html'>
                <select name='color'>
                    <option>256</option>
                    <option>truecolor</option>
                </select>
                <button type='submit'>Just do it</button>
            </form>
        </body>
    </html>''')


for char in TRUEASCII_CHARS:
    TRUEASCII_BLOCKS_1[char] = trueascii_make_char_image(char, '1')
    TRUEASCII_BLOCKS_L[char] = trueascii_make_char_image(char, 'L')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8082, debug=True)


