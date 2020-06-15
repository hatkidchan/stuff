#!/usr/bin/env python3
# Why sine and cosine are offset by 90 degrees?
from basegame import BaseGame, Draw
from pygame.math import *
from math import *
from pygame.locals import *
import pygame.mouse as mouse


def frange(start, end, step=1.0):
    v = start
    while v <= end:
        yield v
        v += step


def hsl_to_rgb(h, s, l):
    r, g, b = 0, 0, 0
    if s == 0:
        r = g = b = l # achromatic
    else:
        def hue2rgb(p, q, t):
            if t < 0: t += 1
            if t > 1: t -= 1
            if t < 1 / 6: return p + (q - p) * 6 * t
            if t < 1 / 2: return q
            if t < 2 / 3: return p + (q - p) * (2/3 - t) * 6
            return p
        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q
        r = hue2rgb(p, q, h + 1 / 3)
        g = hue2rgb(p, q, h)
        b = hue2rgb(p, q, h - 1 / 3)
    return tuple(map(int, map(lambda v: v * 255, [r, g, b])))


class Why90(BaseGame):
    __screen_size__ = (400, 400)
    def ready(self):
        self.offset = [0, 0]
        self.step = 1
        self.draw = Draw(self.surface)
        self.offset_delta = [0, 0]
        self.oclock = 0

    def frame(self, delta):
        self.oclock += delta
        while self.oclock > 0.05:
            self.oclock -= 0.05
            self.offset[0] += self.offset_delta[0]
            self.offset[1] += self.offset_delta[1]

        self.debug['offset_sin'] = '%7.3fdeg' % self.offset[0]
        self.debug['offset_cos'] = '%7.3fdeg' % self.offset[1]

        self.draw.rect(Color('#131313'), self.surface.get_rect())
        for t in frange(0, tau, tau * self.step / 360):
            x = sin(t + (self.offset[1] / 180) * pi)
            y = sin(t + (self.offset[0] / 180) * pi)
            sx = int(200 + x * 90)
            sy = int(200 - y * 90)
            color = Color(*hsl_to_rgb(t / tau, 1, 0.7))
            self.draw.circle(color, (sx, sy), 1, 0)
            if t == 0:
                self.draw.line(color, (200, 200), (sx, sy))
        return True
    
    def event_handler(self, event):
        if event.type == MOUSEBUTTONDOWN:
            if event.button == 4:  # WHEEL_UP
                self.step += 1
            elif event.button == 5:  # WHEEL_DOWN
                self.step = max(1, self.step - 1)
        elif event.type == KEYDOWN:
            self.debug['e'] = str(event)
            if event.key == K_UP:
                self.offset_delta[0] = -1
            elif event.key == K_DOWN:
                self.offset_delta[0] = 1
            elif event.key == K_LEFT:
                self.offset_delta[1] = -1
            elif event.key == K_RIGHT:
                self.offset_delta[1] = 1
        elif event.type == KEYUP:
            if event.key in (K_UP, K_DOWN):
                self.offset_delta[0] = 0
            elif event.key in (K_LEFT, K_RIGHT):
                self.offset_delta[1] = 0

if __name__ == '__main__':
    game = Why90()
    game.mainloop()

