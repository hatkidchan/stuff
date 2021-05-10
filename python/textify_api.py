#!/usr/bin/env python3
from io import StringIO
from textwrap import dedent
from html import escape
from random import choice
from string import ascii_lowercase
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageEnhance
from flask import Flask, request, Response, stream_with_context


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
RESULT_MIN_SIZE = 8, 2  # in characters
RESULT_DEFAULT_SIZE = 80, 24  # in characters
RESULT_MAX_SIZE = 240, 72  # in characters
# True ASCII
TRUEASCII_CHARS = ''.join(chr(c) for c in range(0x20, 0x7f))
TRUEASCII_FONT = ImageFont.load_default()
TRUEASCII_BLOCK_SIZE = TRUEASCII_FONT.getsize(' ')
TRUEASCII_BLOCKS_1 = {}  # will be populated later
TRUEASCII_BLOCKS_L = {}  # will be populated later
# Colorful charmap
COLORFULMAP_DEFAULT_CHARSET = ' ._=*^"13%&@$#'
# Colorful blocks
COLORFULBLK_BLOCK_TOP = '\u2580'
COLORFULBLK_BLOCK_BOT = '\u2584'
COLORFULBLK_BLOCK_FUL = '\u2588'
COLORFULBLK_BLOCK_NUL = ' '

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

def resize_image(image, width, height, keep=False):
    if keep:
        img = image.copy()
        img.thumbnail((width, height))
        return img
    ratio = min(width / image.width, height / image.height)
    return image.resize((int(image.width * ratio), int(image.height * ratio)))

def bool_(v):
    if str(v).lower() in ['yes', 'true', 'on']:
        return True
    if str(v).lower() in ['no', 'false', 'off']:
        return False
    return bool(int(v)) if str(v).isnumeric() else bool(v)

def clamp(v, a, b):
    a, b = min([a, b]), max([a, b])
    return min(b, max(a, v))

def avg_color(img, x, y, w, h):
    data = img.crop((x, y, x + w, y + h)).convert('RGB').getdata()
    rs, gs, bs = (sum(px[i] for px in data) for i in range(3))
    sz = w * h
    return rs / sz, gs / sz, bs / sz

def get_param(k, default=None, type_=str):
    try:
        return type_(request.args.get(k, request.values.get(k, default)))
    except Exception:
        return type_(default)


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

######################################################################
#   WEB EXAMPLES                                                     #
######################################################################
WEB_PAGE_TEMPLATE = """<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>textify_api</title>
    <style>
pre, input[type=text] {
  font-family: Consolas, monospace;
}
html, body {
  background: #131313;
  color: #efefef;
}
input, button, select {
  background: #262626;
  color: #cfcffa;
  border: 1px solid black;
  border-radius: 0px;
}
input[type=range] {
  width: 400px;
}
pre {
    font-size: 14px;
}
    </style>
  </head>
  <body>
$$FORMS$$
  <script>
// http://stackoverflow.com/questions/1779858/ddg#7685469
var escapeShell = function(cmd) {
  return '"'+cmd.replace(/(["\s'$`\\\\])/g,'\\\\$1')+'"';
};

document.querySelectorAll("form").forEach(function(form, i, a) {
  var update_form = function() {
    var command = "curl -X" + form.method.toUpperCase();
    form.querySelectorAll("select, input").forEach(function(el) {
      var value_elem = el.parentElement.parentElement.querySelectorAll("td")[2];
      command += "\\n     -F" + el.name + "=";
      if (el.nodeName == "SELECT") {
        command += el.value;
        value_elem.innerText = el.value;
      } else {
        switch (el.type) {
          case "file":
            if (el.files[0])
              command += (value_elem.innerText = escapeShell(el.files[0].name));
            else
              command += (value_elem.innerText = "image.png");
            break;
            
          case "checkbox":
            command += (value_elem.innerText = el.checked ? "true" : "false");
            break;
            
          case "range":
            command += el.value;
            value_elem.innerText = el.value;
            break;
            
          default:
            command += escapeShell(el.value);
            value_elem.innerText = escapeShell(el.value);
            break;
        }
      }
    });
    command += "\\n     " + form.action;
    form.querySelector("pre").innerText = command;
  };
  update_form();
  form.addEventListener("change", update_form);
  form.addEventListener("input", update_form);
  form.addEventListener("submit", function(se) {
    if (!form.querySelector("input[name=image]").files[0]) {
      se.preventDefault();
      form.querySelector("input[name=image]").click();
      return false;
    }
  });

  var inline_window = form.querySelectorAll("details")[1],
      preview_elem = inline_window.querySelector("pre");
  inline_window.querySelector("button").addEventListener("click", function(e) {
    var data = new FormData(form);
    data.delete("html");
    data.delete("without_container");
    data.append("html", "true");
    data.append("without_container", "true");
    var xhr = new XMLHttpRequest();
    xhr.open(form.method, form.action);
    xhr.onload = function(le) {
      var rows = xhr.getResponseHeader("X-Result-Rows"),
          cols = xhr.getResponseHeader("X-Result-Cols");
      var status = "Size: " + +cols + "x" + +rows;
      preview_elem.innerHTML = status + "\\n" + xhr.responseText;
      inline_window.querySelector("button").disabled = "";
    };
    xhr.onerror = xhr.onabort = function(le) {
      inline_window.querySelector("button").disabled = "";
    };
    xhr.addEventListener("progress", function(pe) {
      var rows = xhr.getResponseHeader("X-Result-Rows"),
          cols = xhr.getResponseHeader("X-Result-Cols");
      var progress = xhr.responseText.match(/\\n/g).length / rows;
      var status = "Size: " + +cols + "x" + +rows;
      status += " (" + (progress * 100).toFixed(2) + "% done)";
      preview_elem.innerHTML = status + "\\n" + xhr.responseText;
    });
    inline_window.querySelector("button").disabled = "disabled";
    xhr.send(data);
    e.preventDefault();
    return false;
  });
});
var set_default_value = function(e) {
  if (e.ctrlKey && e.target.defaultValue !== undefined) {
    e.target.value = e.target.defaultValue;
    if ("createEvent" in document) {
      var evt = document.createEvent("HTMLEvents");
      evt.initEvent("change", false, true);
      e.target.dispatchEvent(evt);
      e.target.form.dispatchEvent(evt);
    } else
      e.target.fireEvent("onchange");
  }
}
  </script>
  </body>
</html>
"""
WEB_FORM_TEMPLATE = """
<h1>{url}</h1>
<form method="POST" action="{url}" enctype="multipart/form-data">
  <table>
    <tr><th>key</th><th>input</th><th>value</th></tr>
{fields}
  </table>
  <button type="submit">Submit</button>
  <details>
    <summary>cUrl command</summary>
    <pre></pre>
  </details>
  <details>
    <summary>Inline view</summary>
    <button>Update</button>
    <pre></pre>
  </details>
</form>
<hr>
"""
WEB_FIELD_TEMPLATE = """
<tr>
  <td><label for="{key}">{title}</label></td>
  <td>{input}</td>
  <td>N/A</td>
</tr>
"""

def form_param(name, type_="text", title="", **options):
    def decorate(func):
        if not hasattr(func, "_form"):
            func._form = { "image": { 
                "type": "file",
                "title": "Source image"
            }}
        if "value" in options:
            options["defaultValue"] = options["value"]
        func._form[name] = dict(type=type_, title=title, **options)
        return func
    return decorate

def make_input(name, field):
    output = ""
    if field["type"] == "select":
        output += "<select name=\"%s\">" % name
        for val in field["values"]:
            output += "<option>%s</option>" % val
        output += "</select>"
    elif field["type"] == "file":
        uid = "file_" + str.join("", [choice(ascii_lowercase) for _ in range(10)])
        output = "<input name=\"%s\" hidden id=\"%s\" type=\"file\">" % (name, uid)
        output += "<button onclick=\""
        output += "document.getElementById('%s').click()" % uid
        output += "; event.preventDefault(); return false\">Open file</button>"
    else:
        output += "<input name=\"%s\"" % name
        for (k, v) in field.items():
            output += " %s=%r" % (k, escape(str(v)))
        output += " onclick=\"set_default_value(event);\""
        output += ">"
    return output

app = Flask(__name__)


@app.route('/conv/trueascii', methods=['POST'])
@form_param("bitmap", "checkbox", "Use dithering")
@form_param("enhance", "checkbox", "Pre-process alpha layer")
@form_param("brightest", "range", "Brightness", min=0, max=10, step=.1, value=1)
@form_param("contrast", "range", "Contrast", min=0, max=10, step=.1, value=1)
@form_param("html", "checkbox", "Output as HTML")
@form_param("without_container", "checkbox", "Do not enclose in PRE")
@form_param("charmap", "text", "Charset", value=TRUEASCII_CHARS)
@form_param("color", "select", "Color mode", values=["no", "256", "truecolor"])
@form_param("rows", "range", "Number of lines", min=RESULT_MIN_SIZE[1],
        max=RESULT_MAX_SIZE[1], step=1, value=RESULT_DEFAULT_SIZE[1])
@form_param("cols", "range", "Width of line", min=RESULT_MIN_SIZE[0],
        max=RESULT_MAX_SIZE[0], step=1, value=RESULT_DEFAULT_SIZE[0])
def conv_trueascii():
    if 'image' not in request.files:
        raise KeyError('no image sent')
    bitmap = get_param('bitmap', False, bool_)
    enhance = get_param('enhance', True, bool_)
    contrast = get_param('contrast', 1.5, float)
    brightness = get_param('brightness', 1.5, float)
    html = get_param('html', False, bool_)
    without_container = get_param('without_container', False, bool_)
    charmap = set(get_param('charmap', TRUEASCII_CHARS, str))
    color = get_param('color', 'no', str)
    rows = get_param('rows', RESULT_DEFAULT_SIZE[1], int)
    cols = get_param('cols', RESULT_DEFAULT_SIZE[0], int)
    rows = clamp(rows, RESULT_MIN_SIZE[1], RESULT_MAX_SIZE[1])
    cols = clamp(cols, RESULT_MIN_SIZE[0], RESULT_MAX_SIZE[0])
    
    if color not in ('no', 'truecolor', '256'):
        raise KeyError('unknown color mode, supported only no/256/truecolor')

    image = Image.open(request.files['image']).convert('RGB')
    if color != 'no':
        image_color = resize_image(image,
                                   cols * TRUEASCII_BLOCK_SIZE[0],
                                   rows * TRUEASCII_BLOCK_SIZE[1])
    if enhance:
        image = ImageEnhance.Brightness(image).enhance(brightness)
        image = ImageEnhance.Contrast(image).enhance(contrast)
    image = resize_image(image.convert('1' if bitmap else 'L'), 
                         cols * TRUEASCII_BLOCK_SIZE[0],
                         rows * TRUEASCII_BLOCK_SIZE[1])
    
    rows = image.height // TRUEASCII_BLOCK_SIZE[1]
    cols = image.width // TRUEASCII_BLOCK_SIZE[0]
    
    charmap = list(filter(lambda c: c in TRUEASCII_CHARS, charmap))

    def process():
        if html and not without_container:
            yield '<!-- Remove line bellow in case of embedding -->\n'
            yield '<style>html,body{background:#000;}</style>\n'
            yield '<pre style="background:#000000;color:#ffffff">\n'
        for y in range(rows):
            line = ''
            oc = None
            for x in range(cols):
                x1 = x * TRUEASCII_BLOCK_SIZE[0]
                y1 = y * TRUEASCII_BLOCK_SIZE[1]
                if color != 'no':
                    c = avg_color(image_color, x1, y1, *TRUEASCII_BLOCK_SIZE)
                    c = map(int, c)
                    if color == '256':
                        c = vt100rgb(*c)
                    c = tuple(c)
                    if c != oc:
                        if oc is not None:
                            line += HTML_CLOSE
                        if html:
                            line += HTML_FOREGROUND % c
                        else:
                            line += SEQ_TRUECOLOR_FG % c
                        oc = c
                line += escape(trueascii_probe_char(image, x, y, charmap))
            if oc is not None:
                line += HTML_CLOSE if html else "\x1b[0m"
            yield line + '\n'
        if html and not without_container:
            yield '</pre>'
    response = Response(stream_with_context(process()))
    response.headers['Content-type'] = ('text/html' if html else 'text/plain'
                                        + '; charset=utf-8')
    response.headers['X-Result-Rows'] = rows
    response.headers['X-Result-Cols'] = cols
    return response


@app.route('/conv/charmap', methods=['POST'])
@form_param("html", "checkbox", "Output as HTML")
@form_param("without_container", "checkbox", "Do not enclose in PRE")
@form_param("charmap", "text", "Charset", value=COLORFULMAP_DEFAULT_CHARSET)
@form_param("color", "select", "Color mode", values=["no", "256", "truecolor"])
@form_param("rows", "range", "Number of lines", min=RESULT_MIN_SIZE[1],
        max=RESULT_MAX_SIZE[1], step=1, value=RESULT_DEFAULT_SIZE[1])
@form_param("cols", "range", "Width of line", min=RESULT_MIN_SIZE[0],
        max=RESULT_MAX_SIZE[0], step=1, value=RESULT_DEFAULT_SIZE[0])
def conv_charmap():
    if 'image' not in request.files:
        raise KeyError('no image sent')
    image = Image.open(request.files['image'])
    color = get_param('color', 'no', str)
    html = get_param('html', False, bool_)
    without_container = get_param('without_container', False, bool_)
    if color not in ['no', '256', 'truecolor']:
        raise KeyError('unknown color mode, supported only no/256/truecolor')
    image = image.convert('L' if color == 'no' else 'RGB')
    charmap = get_param('charmap', COLORFULMAP_DEFAULT_CHARSET)
    rows = get_param('rows', RESULT_DEFAULT_SIZE[1], int)
    cols = get_param('cols', RESULT_DEFAULT_SIZE[0], int)
    rows = clamp(rows, RESULT_MIN_SIZE[1], RESULT_MAX_SIZE[1])
    cols = clamp(cols, RESULT_MIN_SIZE[0], RESULT_MAX_SIZE[0])
    
    image = resize_image(image, cols, rows * 2, 1)
    image = image.resize((image.width, image.height // 2))
    
    def process():
        if html and not without_container:
            yield '<pre style="background:#000000;color:#ffffff">'
        for y in range(image.height):
            line = ''
            for x in range(image.width):
                v = image.getpixel((x, y))
                if color == 'no':
                    line += charmap[int(len(charmap) * v / 256)]
                else:
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
                    p = sum(v) / 768
                    line += charmap[int(len(charmap) * p)]
                    if html:
                        line += HTML_CLOSE
            yield line + '\n' + ('\x1b[0m' if color != 'no' and not html else '')
        if html and not without_container:
            yield '</pre>'
    response = Response(stream_with_context(process()))
    response.headers['Content-type'] = ('text/html' if html else 'text/plain'
                                        + '; charset=utf-8')
    response.headers['X-Result-Rows'] = image.height;
    response.headers['X-Result-Cols'] = image.width;
    return response


@app.route('/conv/blocks', methods=['POST'])
@form_param("html", "checkbox", "Output as HTML")
@form_param("without_container", "checkbox", "Do not enclose in PRE")
@form_param("color", "select", "Color mode", values=["256", "truecolor"])
@form_param("rows", "range", "Number of lines", min=RESULT_MIN_SIZE[1],
        max=RESULT_MAX_SIZE[1], step=1, value=RESULT_DEFAULT_SIZE[1])
@form_param("cols", "range", "Width of line", min=RESULT_MIN_SIZE[0],
        max=RESULT_MAX_SIZE[0], step=1, value=RESULT_DEFAULT_SIZE[0])
def conv_post():
    if 'image' not in request.files:
        raise KeyError('no image sent')
    color = get_param('color', 'truecolor')
    html = get_param('html', False, bool_)
    without_container = get_param('without_container', False, bool_)
    if color not in ['256', 'truecolor']:
        raise KeyError('unknown color mode, supported only 256 or truecolor')
    rows = get_param('rows', RESULT_DEFAULT_SIZE[1], int)
    cols = get_param('cols', RESULT_DEFAULT_SIZE[0], int)
    rows = clamp(rows, RESULT_MIN_SIZE[1], RESULT_MAX_SIZE[1])
    cols = clamp(cols, RESULT_MIN_SIZE[0], RESULT_MAX_SIZE[0])

    image = Image.open(request.files['image']).convert('RGBA')
    image = resize_image(image, cols, rows * 2, 1)

    def process():
        if html and not without_container:
            yield '<pre style="background:#000000;color:#ffffff">'
        for y in range(0, image.height, 2):
            line = ''
            for x in range(image.width):
                *rgb1, a1 = image.getpixel((x, y))
                *rgb2, a2 = image.getpixel((x, y + 1))
                a1, a2 = a1 >= 127, a2 >= 127
                if color == '256':
                    rgb1, rgb2 = vt100rgb(*rgb1), vt100rgb(*rgb2)
                rgb1, rgb2 = tuple(rgb1), tuple(rgb2)

                if not a1 and not a2:   # transparent
                    line += COLORFULBLK_BLOCK_NUL;
                elif a1 and not a2:     # only top
                    if html:
                        line += HTML_FOREGROUND % rgb1
                    elif color == '256':
                        line += SEQ_VT100_FG % rgb2vt100(*rgb1)
                    else:
                        line += SEQ_TRUECOLOR_FG % rgb1
                    line += COLORFULBLK_BLOCK_TOP
                    if html:
                        line += HTML_CLOSE
                    else:
                        line += '\x1b[0m'
                elif not a1 and a2:     # only bottom
                    if html:
                        line += HTML_FOREGROUND % rgb2
                    elif color == '256':
                        line += SEQ_VT100_FG % rgb2vt100(*rgb2)
                    else:
                        line += SEQ_TRUECOLOR_FG % rgb2
                    line += COLORFULBLK_BLOCK_BOT
                    if html:
                        line += HTML_CLOSE
                    else:
                        line += '\x1b[0m'
                else:                   # normal behavior
                    c1, c2 = None, None
                    if html:
                        c1 = HTML_BACKGROUND % rgb1
                        c2 = HTML_FOREGROUND % rgb2
                    elif color == '256':
                        c1 = SEQ_VT100_BG % rgb2vt100(*rgb1)
                        c2 = SEQ_VT100_FG % rgb2vt100(*rgb2)
                    else:
                        c1 = SEQ_TRUECOLOR_BG % rgb1
                        c2 = SEQ_TRUECOLOR_FG % rgb2

                    if rgb1 == rgb2:
                        line += c2 + COLORFULBLK_BLOCK_FUL
                    else:
                        line += c1 + c2 + COLORFULBLK_BLOCK_BOT
                    if html:
                        line += HTML_CLOSE * (1 if c1 == c2 else 2)
                    else:
                        line += '\x1b[0m'
            yield line + '\n'
        if html and not without_container:
            yield '</pre>'
    response = Response(stream_with_context(process()))
    response.headers['Content-type'] = (('text/html' if html else 'text/plain')
                                         + '; charset=utf-8')
    response.headers['X-Result-Rows'] = image.height // 2;
    response.headers['X-Result-Cols'] = image.width;
    return response


@app.route('/docs')
def docs():
    max_width, max_height = RESULT_MAX_SIZE
    docs_text = f'''
    Shitty docpage about available methods and their parameters
    ======================================================================
    
    /conv/trueascii
        True image to ASCII-art conversion, most accurate yet slowest method.

        Parameters:
            charmap: str = [all chars between 0x20 and 0x7e]
                String of ASCII characters, used while searching best fit
                Empty string may result in a lot of questions.
                Characters outside internal list (described above) will be
                dropped away. Duplicates will be removed too. Order does not
                matter, because characters picked by their mask, not index.
            color: str['no', '256', 'truecolor'] = 'no'
                No comments, just selects palette.
                When ommited or sent as 'no', color is not used
            enhance: bool = false
                Enhancements for "alpha" layer. Applied no matter of color mode,
                but primarily used in it.
            brightness: float = 1.5
                Brightness level for "alpha" layer. 1.0 is source image and
                0.0 is pitch black.
            contrast: float = 1.5
                Contrast level for "alpha" layer. 1.0 is source image and
                0.0 is gray. Works like that thing in old TV's
            html: bool = false
                Should we output result in html-friendly format or not.
            without_container: bool = false
                When true and in HTML mode, just disables parent PRE tag
            rows: int
                Number of rows (horizontal lines) of resulting text.
                Clamped to some numbers which I'm too lazy to write here
            cols: int
                Same as above, but for vertical lines
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
            without_container: bool = false
                When true and in HTML mode, just disables parent PRE tag
            rows: int
                Number of rows (horizontal lines) of resulting text.
                Clamped to some numbers which I'm too lazy to write here
            cols: int
                Same as above, but for vertical lines
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
            without_container: bool = false
                When true and in HTML mode, just disables parent PRE tag
            rows: int
                Number of rows (horizontal lines) of resulting text.
                Clamped to some numbers which I'm too lazy to write here
            cols: int
                Same as above, but for vertical lines

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
    forms = []
    for route in app.url_map.iter_rules():
        handler = globals().get(route.endpoint, None)
        if not hasattr(handler, "_form"):
            continue
        fields = []
        for (name, params) in handler._form.items():
            input_elem = make_input(name, params)
            fields.append(WEB_FIELD_TEMPLATE.format(key=name,
                                                    title=params["title"],
                                                    input=input_elem))
        forms.append(WEB_FORM_TEMPLATE.format(url=route.rule,
                                              fields=str.join("\n", fields)))
    return WEB_PAGE_TEMPLATE.replace("$$FORMS$$", str.join("\n", forms))


for char in TRUEASCII_CHARS:
    TRUEASCII_BLOCKS_1[char] = trueascii_make_char_image(char, '1')
    TRUEASCII_BLOCKS_L[char] = trueascii_make_char_image(char, 'L')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8082, debug=True)


