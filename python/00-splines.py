#!/usr/bin/env python3
# Spline renderer based on oneLoneCoder's video:
# http://www.youtube.com/watch?v=9_aJGUTePYo
from basegame import BaseGame, Draw
from pygame.math import *
from math import *
from time import time
from pygame.locals import *
import pygame.mouse as mouse


SPLINE_CONTROLPOINT = Color('#00fafa')
SPLINE_CONTROLPOINT_SEL = Color('#fa00af')
SPLINE_COLOR = Color('#af00fa')
BACKGROUND_COLOR = Color('#1313137f')


def frange(start, end, step=1.0):
    v = start
    while v <= end:
        yield v
        v += step


class SplinesRenderer(BaseGame):
    __screen_size__ = (800, 500)
    def ready(self):
        self.points = [
                Vector2(10, 41),
                Vector2(40, 41),
                Vector2(70, 41),
                Vector2(100, 41)
        ]
        self.dragging_point = None
        self.panning = None
        self.looped = False
        self.spline_step = 0.1
        self.spline_step_delta = 0
        self.move_delta = {'x': 0, 'y': 0}
        self.draw = Draw(self.surface)
        
    @classmethod
    def get_spline_point(cls, p, t=0, looped=False):
        _t = t
        t = max(min(t, len(p)), 0)
        if not looped:
            p1 = min(int(t) + 1, len(p) - 1)
            p2 = min(p1 + 1, len(p) - 1)
            p3 = min(p2 + 1, len(p) - 1)
            p0 = p1 - 1
        else:
            p1 = int(t) % len(p)
            p2 = (p1 + 1) % len(p)
            p3 = (p1 + 2) % len(p)
            p0 = p1 - 1
    
        t = t % 1
        tt = t ** 2
        ttt = t ** 3
        
        q1 = -ttt + 2 * tt - t
        q2 = 3 * ttt - 5 * tt + 2
        q3 = -3 * ttt + 4 * tt + t
        q4 = ttt - tt
        
        tx = (p[p0].x * q1 + p[p1].x * q2 + p[p2].x * q3 + p[p3].x * q4) / 2
        ty = (p[p0].y * q1 + p[p1].y * q2 + p[p2].y * q3 + p[p3].y * q4) / 2
        return Vector2(tx, ty)
    
    def frame(self, delta):
        self.draw.offset.x += self.move_delta['x'] * delta
        self.draw.offset.y += self.move_delta['y'] * delta
        
        if self.spline_step_delta != 0:
            self.spline_step *= (1 + self.spline_step_delta * delta)
            self.debug['Step'] = f'{self.spline_step:7.5f}'

        self.draw.rect(BACKGROUND_COLOR, self.surface.get_rect(), screen=True)
        
        start = time()
        spline = []
        limit = len(self.points) - (0 if self.looped else 3)
        for t in frange(0, limit, self.spline_step):
            spline.append(self.get_spline_point(self.points, t, self.looped))
        self.debug['Calc'] = f'{time() - start:7.5f}s'
        self.debug['nLines'] = len(spline)
        
        start = time()
        if len(spline) > 1:
            self.draw.lines(SPLINE_COLOR, spline,
                            width=max(1, int(2 * self.draw.scale)),
                            closed=self.looped)
        self.debug['Render'] = f'{time() - start:7.5f}s'

        mwpos = Vector2(self.draw.screen_to_world(*mouse.get_pos()))
        for point in self.points:
            near = mwpos.distance_to(point) < 5
            color = SPLINE_CONTROLPOINT_SEL if near else SPLINE_CONTROLPOINT
            self.draw.circle(color, point, max(int(5 * self.draw.scale), 1), 1)
        return True
    
    def event_handler(self, event):
        if event.type == MOUSEBUTTONDOWN:
            world_mouse_pos = Vector2(self.draw.screen_to_world(*event.pos))
            if event.button == 1:  # LMB
                for i, p in enumerate(self.points):
                    if p.distance_to(world_mouse_pos) < 5:
                        self.dragging_point = i
                        break
                else:
                    self.panning = (event.pos,
                                    (self.draw.offset.x, self.draw.offset.y))
            elif event.button == 2:  # MMB
                for i, p in enumerate(self.points):
                    if p.distance_to(world_mouse_pos) < 5 / self.draw.scale:
                        self.points.pop(i)
                        break
            elif event.button == 3:  # RMB
                self.points.append(world_mouse_pos)
            elif event.button == 4:
                self.draw.zoom_around(*event.pos, 0.1)
                self.debug['Zoom'] = f'x{self.draw.scale:7.5f}'
            elif event.button == 5:
                self.draw.zoom_around(*event.pos, -0.1)
                self.debug['Zoom'] = f'x{self.draw.scale:7.5f}'
            else:
                print('UNHANDLED', event)

        elif event.type == MOUSEBUTTONUP:
            if self.dragging_point is not None:
                self.dragging_point = None
            elif self.panning is not None:
                self.panning = None
            else:
                print('UNHANDLED', event)

        elif event.type == MOUSEMOTION:
            if self.dragging_point is not None:
                world_mouse_pos = Vector2(self.draw.screen_to_world(*event.pos))
                self.points[self.dragging_point] = world_mouse_pos
            elif self.panning is not None:
                mdx = self.panning[0][0] - event.pos[0]
                mdy = self.panning[0][1] - event.pos[1]
                self.draw.offset.x = self.panning[1][0] + mdx / self.draw.scale
                self.draw.offset.y = self.panning[1][1] + mdy / self.draw.scale
            else:
                print('UNHANDLED', event)

        elif event.type == KEYDOWN:
            if event.key == K_z:
                self.spline_step_delta = -0.1
            elif event.key == K_x:
                self.spline_step_delta = 0.1
            elif event.key == K_l:
                self.looped = not self.looped
            elif event.key == K_i:
                pos = Vector2(self.draw.screen_to_world(*mouse.get_pos()))
                self.points.append(pos)
            elif event.key == K_UP:
                self.move_delta['y'] = -100
            elif event.key == K_DOWN:
                self.move_delta['y'] = 100
            elif event.key == K_LEFT:
                self.move_delta['x'] = -100
            elif event.key == K_RIGHT:
                self.move_delta['x'] = 100
            elif event.key == K_ESCAPE:
                self.stop()
            else:
                print('UNHANDLED', event)

        elif event.type == KEYUP:
            if event.key in [K_z, K_x]:
                self.spline_step_delta = 0
            elif event.key in [K_UP, K_DOWN]:
                self.move_delta['y'] = 0
            elif event.key == [K_LEFT, K_RIGHT]:
                self.move_delta['x'] = 0
            else:
                print('UNHANDLED', event)
        else:
            print('UNHANDLED', event)
    

if __name__ == '__main__':
    game = SplinesRenderer()
    game.mainloop()

