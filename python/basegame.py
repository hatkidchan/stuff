#!/usr/bin/env python3
import pygame
from pygame import Color, Rect, draw
import pygame.draw as draw
import pygame.mouse as mouse
from pygame.locals import *
from pygame.math import *
from traceback import format_exc


EMPTY = Color('#00000000')
RED = Color('#ff0000ff')
BLACK = Color('#000000ff')


class AvgCollector:
    def __init__(self, initial=1, samples=10):
        self.samples = [initial for _ in range(samples)]
        self.nsamples = samples

    def push(self, value):
        self.samples.append(value)
        if len(self.samples) > self.nsamples:
            self.samples.pop(0)

    def value(self):
        return sum(self.samples) / len(self.samples)


class TSurface(pygame.Surface):
    pass


class Draw:
    def __init__(self, surface):
        self.surface = surface
        self.offset = Vector2(0, 0)
        self.scale = 1

    def world_to_screen(self, wx, wy):
        return ((wx - self.offset.x) * self.scale,
                (wy - self.offset.y) * self.scale)

    def screen_to_world(self, sx, sy):
        return ((sx / self.scale) + self.offset.x,
                (sy / self.scale) + self.offset.y)

    def zoom_around(self, wx, wy, factor=0):
        owmx, owmy = self.screen_to_world(wx, wy)
        self.scale *= (1 + factor)
        nwmx, nwmy = self.screen_to_world(wx, wy)
        self.offset.x += (owmx - nwmx)
        self.offset.y += (owmy - nwmy)

    def _vec2_to_screen(self, vec2):
        vec2 = Vector2(vec2)
        x, y = map(int, self.world_to_screen(vec2.x, vec2.y))
        return x, y

    def _rect_to_screen(self, rect):
        rect = Rect(rect)
        scale = self.scale
        x, y = map(int, self.world_to_screen(rect.x, rect.y))
        w, h = map(int, [rect.width * scale, rect.height * scale])
        return Rect(x, y, w, h)

    def rect(self, color, rect, width=0, border_radius=0, screen=False):
        rect = rect if screen else self._rect_to_screen(rect)
        return draw.rect(self.surface, color, rect, width)

    def polygon(self, color, points, width=0, screen=False):
        points = points if screen else list(map(self._vec2_to_screen, points))
        return draw.rect(self.surface, color, points, width)
        
    def circle(self, color, center, radius, width=0, screen=False):
        center = center if screen else self._vec2_to_screen(center)
        return draw.circle(self.surface, color, center, radius, width)
        
    def ellipse(self, color, rect, width=0, screen=False):
        rect = rect if screen else self._rect_to_screen(rect)
        return draw.ellipse(self.surface, color, rect, width)
        
    def arc(self, color, rect, start, stop, width=1, screen=False):
        rect = rect if screen else self._rect_to_screen(rect)
        return draw.arc(self.surface, color, rect, start, stop, width)
        
    def line(self, color, start, end, width=1, screen=False):
        start = start if screen else self._vec2_to_screen(start)
        end = end if screen else self._vec2_to_screen(end)
        return draw.line(self.surface, color, start, end, width)

    def lines(self, color, points, closed=False, width=1, screen=False):
        points = points if screen else list(map(self._vec2_to_screen, points))
        return draw.lines(self.surface, color, closed, points, width)

    def aaline(self, color, start, end, width=1, screen=False):
        start = start if screen else self._vec2_to_screen(start)
        end = end if screen else self._vec2_to_screen(end)
        return draw.aaline(self.surface, color, start, end, width)

    def aalines(self, color, points, closed=False, width=1, screen=False):
        points = points if screen else list(map(self._vec2_to_screen, points))
        return draw.aalines(self.surface, color, closed, points, width)


class BaseGame():
    __screen_size__ = None
    def __init__(self, size=(400, 400), fps_limit=120):
        if not pygame.font.get_init():
            pygame.font.init()
        if self.__screen_size__ is not None:
            size = self.__screen_size__
        self.__screen = pygame.display.set_mode(size)
        self.surface = TSurface(size, pygame.SRCALPHA)
        self.surface_d = TSurface(size, pygame.SRCALPHA)
        self.font_d = pygame.font.SysFont('monospace', 14)
        self.clock = pygame.time.Clock()
        self._fps_limit = fps_limit
        self.__avg_fps = AvgCollector(0, int(self._fps_limit * 0.5))
        self.debug = {}
        self.__stop = False
        self.__lock = False
        self._debug = True
        self._n_frames = 0
        setattr(self.surface, '_GAME', self)
        self.ready()

    def mainloop(self):
        redraw = True
        while not self.__stop:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.__stop = True
                        return
                    if not self.__lock:
                        self.event_handler(event)
                    elif event.type == pygame.KEYDOWN:
                        self.__stop = True
                        return
            except Exception as e:
                self.draw_error(e, 'event handler')
                self.__lock = True
            
            if not self.__lock:
                try:
                    frame_delta = self.clock.tick(self._fps_limit) / 1000
                    redraw = self.frame(frame_delta)
                    self.__avg_fps.push(1 / frame_delta)
                except Exception as e:
                    self.draw_error(e, 'renderer')
                    self.__lock = True
            
            if not self.__lock and self._debug:
                self.debug['FPS'] = f'{self.__avg_fps.value():5.1f}'

                draw.rect(self.surface_d, EMPTY, self.surface_d.get_rect())
                for i, (k, v) in enumerate(list(self.debug.items())):
                    if isinstance(v, tuple):
                        v, color = v
                    else:
                        color = Color('#ffffff')
                    line = self.font_d.render(f'{k}: {v}', True, color)
                    self.surface_d.blit(line, (0, i * 16))
            
            if redraw:
                self.__screen.blit(self.surface, (0, 0))
            if redraw or self.__lock:
                if self._debug or self.__lock:
                    self.__screen.blit(self.surface_d, (0, 0))
                pygame.display.flip()
                self._n_frames += 1
    
    def ready(self):
        self.draw = Draw(self.surface)

    def frame(self, delta):
        draw.rect(self.surface, RED, self.surface.get_rect())
        self.draw.line(BLACK, Vector2(0, 0),
                       Vector2(self.draw.screen_to_world(*mouse.get_pos())))
        return True

    def event_handler(self, event):
        print(event.type, event)
    
    def stop(self):
        self.__stop = True
        
    def draw_error(self, e, block='<unknown>'):
        draw.rect(self.surface_d, Color('#131313'), self.surface_d.get_rect())
        lines = []
        lines.append(f'{e!r} occurred in {block}')
        lines += format_exc().split('\n')
        for i, line in enumerate(lines):
            print(line)
            surf = self.font_d.render(line, True, RED, Color('#131313'))
            self.surface_d.blit(surf, (0, i * 16))

if __name__ == '__main__':
    game = BaseGame()
    game.mainloop()

