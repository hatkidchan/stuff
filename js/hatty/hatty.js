var hatty_logo = ' _   _      _____ _______   __\n';
hatty_logo += '| | | | __ |_   _|_   _\\ \\ / /\n'
hatty_logo += '| |_| |/ _` || |   | |  \\ V /\n'
hatty_logo += '|  _  | (_| || |   | |   | |\n'
hatty_logo += '|_| |_|\\__,_||_|   |_|   |_|\n'



function HaTTY(elem, opts) {
  opts = opts || {};
  this.elem = elem;
  this.ctx = elem.getContext('2d');
  this.palette = opts.palette || termpalettes.twilight;
  this.size = { 
    w: opts.size_x || 80,
    h: opts.size_y || 25
  };
  this.charsize = {
    w: opts.char_w || 10,
    h: opts.char_h || 20 
  };
  this.charoffset = {
    x: opts.char_x || 0,
    y: opts.char_y || 0 
  };
  this.font = opts.font || '16px UbuntuMono';

  this.cursor = { y: 0, x: 0, fg: this.palette['default'], bg: 'transparent' };
    
  this.elem.width = this.charsize.w * this.size.w;
  this.elem.height = this.charsize.h * this.size.h;
  
  this.buf = '';
  this._csi = false;
  this._esc = false;
    
  this._rgb2hex = function(r, g, b) { 
    var rh = (r < 16 ? '0' : '') + r.toString(16);
    var gh = (g < 16 ? '0' : '') + g.toString(16);
    var bh = (b < 16 ? '0' : '') + b.toString(16);
    return '#' + rh + gh + bh;
  }
  
  this._pal256torgb = function(i) {
    i = parseInt(i);
    if(i < 16) return this.palette[i];
    else if(i >= 232 && i <= 255) {
      var c = Math.floor(((i - 232) / 24) * 255);
      return this._rgb2hex(c, c, c);
    } else {
      i -= 16;
      var b = (i % 6) * 42;
      i = Math.floor(i / 6);
      var g = (i % 6) * 42;
      i = Math.floor(i / 6);
      var r = (i % 6) * 42;
      return this._rgb2hex(r, g, b);
    }
  }
  
  this._extract_truecolor = function(rgb) {
    var r = parseInt(rgb[0]);
    var g = parseInt(rgb[1]);
    var b = parseInt(rgb[2]);
    return this._rgb2hex(r, g, b);
  }
  
  this._get_color = function(code, parts, bg) {
    bg = bg || false;
    if(code == 38 || code == 48) {
      var type = parts.splice(0, 1)[0];
      if(type == 2)
        return this._extract_truecolor(parts.splice(0, 3));
      else if(type == 5)
        return this._pal256torgb(parts.splice(0, 1)[0]);
      else if(bg)
        throw new Error('unknown extended background palette: ' + type);
      else
        throw new Error('unknown extended foreground palette: ' + type);
    }
    else if(code >= 30 && code <= 37 || code >= 40 && code <= 47)
      return this.palette[code % 10];
    else if(code >= 90 && code <= 97 || code >= 100 && code <= 107)
      return this.palette[(code % 10) + 8];
  }

  this.putc = function(c, force) {
    force = force || false;
    if(c == '\x1b' && !force) {
      if(this.buf.length > 0) {
        this.putc(c, true);
        this.buf = '';
        this._esc = false;
        this._csi = false;
        return this;
      } else {
        this.buf = '';
        this._esc = true;
        this._csi = false;
      }
    } else if((this.buf.length > 0 || this._esc) && !force) {
      if(c == '[') {
        this._csi = true;
        return this;
      } else if(this._csi) {
        if(c == 'm') {
          var parts = this.buf.split(';');
          while(parts.length > 0) {
            var part = parseInt(parts.splice(0, 1)[0]);
            if(part == 0) {
              this.cursor.bg = 'transparent';
              this.cursor.fg = this.palette['default'];
            } else if(part >= 30 && part <= 38 || part >= 90 && part <= 97) {
              this.cursor.fg = this._get_color(part, parts, false);
            } else if(part >= 40 && part <= 48 || part >= 100 && part <= 107) {
              this.cursor.bg = this._get_color(part, parts, true);
            } else {
              throw new Error('unknown color: ' + part, parts);
            }
          }
          this._csi = false;
          this._esc = false;
          this.buf = '';
        } else if(c == '') {
          // TODO: arrows
        } else {
          this.buf += c;
          return this;
        }
      }
    } else if(c == '\n') {
      this.cursor.y++;
      this.cursor.x = 0;
      if(this.cursor.y >= this.size.h) {
        this.cursor.y = this.size.h - 1;
        var copy = this.clone_image();
        this.clear();
        this.ctx.beginPath();
        this.ctx.drawImage(copy, 0, -this.charsize.h);
        this.ctx.closePath();
      }
    } else if(c == '\r') {
      this.cursor.x = 0;
    } else {
      this._insert(this.cursor.y, this.cursor.x,
                   this.cursor.fg, this.cursor.bg, c);
      this.cursor.x++;
      if(this.cursor.x > this.size.w) {
        this.cursor.y++;
        if(this.cursor.y >= this.size.h) {
          this.cursor.y = this.size.h - 1;
          var copy = this.clone_image();
          this.clear();
          this.ctx.beginPath();
          this.ctx.drawImage(copy, 0, -this.charsize.h);
          this.ctx.closePath();
       }
       this.cursor.x = 0;
      }
    }
    return this;
  }
  
  this._insert = function(y, x, fg, bg, c) {
    this.ctx.textAlign = 'left';
    this.ctx.textBaseline = 'top';
    this.ctx.font = this.font;
    this.ctx.beginPath();
    this.ctx.fillStyle = bg;
    if(bg == 'transparent')
      this.ctx.clearRect(x * this.charsize.w, y * this.charsize.h,
                         this.charsize.w, this.charsize.h);
    else
      this.ctx.fillRect(x * this.charsize.w, y * this.charsize.h,
                        this.charsize.w, this.charsize.h);
    this.ctx.closePath();
    this.ctx.beginPath();
    this.ctx.fillStyle = fg;
    this.ctx.fillText(c, x * this.charsize.w + this.charoffset.x,
                         y * this.charsize.h + this.charoffset.y);
    this.ctx.fill();
    this.ctx.closePath();
  }
  
  this.write = function(s) {
    for(var i = 0; i < s.length; i++)
      this.putc(s[i]);
    return this;
  }
  
  this._slow_write = function(s, cps, resolve) {
    if(s.length == 0) return resolve(true);
    this.write(s[0]);
    s = s.slice(1);
    var self = this;
    setTimeout(function() {
      self._slow_write(s, cps, resolve);
    }, 1000 / cps);
  }

  this.slow_write = function(s, cps) {
    var self = this;
    return new Promise(function(resolve, reject) {
      self._slow_write(s, cps, resolve)
    });
  }
  
  this.reset = function() {
    this.clear();
    this.cursor.x = 0;
    this.cursor.y = 0;
    this.write('\x1b[0m');
  }
  
  this.clear = function() {
    this.ctx.beginPath();
    this.ctx.clearRect(0, 0, this.ctx.canvas.width, this.ctx.canvas.height);
    this.ctx.closePath();
  }
  
  this.clone_image = function() {
    var copy = document.createElement('canvas');
    copy.width = this.ctx.canvas.width;
    copy.height = this.ctx.canvas.height;
    copy.getContext('2d').drawImage(this.ctx.canvas, 0, 0);
    return copy;
  }
  
  this.test = function() {
    var self = this;
    this.write('\x1b[91mTesting NOW!');
    this.reset();
    return new Promise(function(resolve) {
      self.slow_write(hatty_logo, 200).then(function() {
        self.write('\x1b[92mweb\x1b[96m@\x1b[92mhatkid.cf \x1b[34m~\n');
        self.write('\x1b[92m$\x1b[0m ');
        self.slow_write('test-term\n', 10).then(function() {
          var text = Array.from(Array(50).keys()).join('\n');
          self.slow_write(text + '\n', 100).then(function() {
            self.write(' * Flood test done\n');
            self.reset();
            self.write('\x1b[95mPowered by\x1b[0m\n');
            self.write(hatty_logo);
            self.write(' * Test default colors ');
            for(var i = 30; i <= 37; i++)
              self.write('\x1b[' + i + 'm' + i + '\x1b[0m ');
            for(var i = 40; i <= 47; i++)
              self.write('\x1b[' + i + 'm' + i + ' \x1b[0m ');
            self.write('\n');
        
            self.write(' * Test bright colors  ');
            for(var i = 90; i <= 97; i++)
              self.write('\x1b[' + i + 'm' + i + '\x1b[0m ');
            for(var i = 100; i <= 107; i++)
              self.write('\x1b[' + i + 'm' + i + '\x1b[0m ');
            self.write('\n');
  
            var s_truecolor = 'Truecolor test! ';
            var x, y, z, r, g, b, r2, g2, b2;
            for(var i = 0; i <= 5; i++) {
              for(var j = 0; j < 80; j++) {
                x = Math.cos((Math.PI * 2 * (i * 2 + j)) / 85 + Math.PI * 0);
                y = Math.cos((Math.PI * 2 * (i * 2 + j)) / 85 + Math.PI * 0.33);
                z = Math.cos((Math.PI * 2 * (i * 2 + j)) / 85 + Math.PI * 0.67);
                r = Math.floor(Math.abs(x * 255));
                g = Math.floor(Math.abs(y * 255));
                b = Math.floor(Math.abs(z * 255));
                r2 = Math.floor(r / 2);
                g2 = Math.floor(g / 2);
                b2 = Math.floor(b / 2);
                self.write('\x1b[48;2;' + r + ';' + g + ';' + b + 'm');
                self.write('\x1b[38;2;' + r2 + ';' + g2 + ';' + b2 + 'm');
                var c = s_truecolor[(i * 80 + j) % s_truecolor.length];
                self.write(c + '\x1b[0m');
              }
              self.write('\n');
            }
            
            for(var i = 0; i < 256; i++) {
              self.write('\x1b[38;5;' + i + 'm' + (i % 10));
            }
            self.write('\x1b[0m\n');
            self.write(' * Test slow typing: ');
            var text = '\x1b[33m[\x1b[\x1b[34m=========================\x1b[33m]';
            self.slow_write(text, 9).then(function() {
              self.write('\r\x1b[92m[PASS]\x1b[33m[\x1b[0m\n');
              self.write(' * All tests done\n');
              self.write('\x1b[92mweb\x1b[96m@\x1b[92mhatkid.cf \x1b[34m~\n');
              self.write('\x1b[92m$\x1b[0m ');
              resolve(true);
            }); // slow-typing
          }); // flood-test
        }); // test-term
      }); // hatty_logo
    }); // promise
  }
}
