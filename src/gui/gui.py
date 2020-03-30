
import time, math
from collections import deque

import pygame
from pygame.locals import *

def scale_values(values, yrange, rect):
    x0, y0, x1, y1 = rect
    ymin, ymax = yrange
    numvals = float(len(values))
    width = x1 - x0
    height = y1 - y0
    vscale = height / (ymax - ymin)
    for n,v in enumerate(values):
        x = ((n / numvals) * width) + x0
        y = ((v - ymin) * vscale) + y0
        yield (x,y)

def draw_graph(surf, rect, values, yrange, reflines, color, width=3):
    pts = list(scale_values(values, yrange, rect))
    pygame.draw.lines(surf, color, False, pts, width)



cyan = (127,255,223)


class TextRectRenderer(object):
    def __init__(self, screen, rect,  header, unit, fontcolor=(255,255,255), bordercolor=(95,63,63), borderwidth=3, bgcolor=(0,0,0)):
        self.screen = screen
        self.rect = rect
        self.header = header
        self.unit = unit
        self.bordercolor = bordercolor
        self.borderwidth = borderwidth
        self.fontcolor = fontcolor
        self.bgcolor = bgcolor
        self.size = rect.size
        self.width = self.size[0]
        self.height = self.size[1]
        self.relrect = pygame.Rect(0, 0, self.rect.width, self.rect.height)
        self.surf = pygame.Surface(self.size)
        self.hA = self.height * 0.75
        self.hB = self.height * 0.25
        self.smallfont = pygame.font.SysFont("menlottc", int(self.height * 0.20))
        self.largefont = pygame.font.SysFont("menlottc", int(self.height * 0.40))
        self.headertxt = self.smallfont.render(header, True, fontcolor, bgcolor)
        self.unittxt = self.smallfont.render(unit, True, fontcolor, bgcolor)

    def render(self, value):
        self.surf.fill(self.bgcolor)
        self.surf.blit(self.headertxt, (0,0))
        self.surf.blit(self.unittxt, (0,self.hA))
        value = self.smallfont.render(str(value), True, self.fontcolor, self.bgcolor)
        self.surf.blit(value, (0,self.hB))
        pygame.draw.rect(self.surf, self.bordercolor, self.relrect, self.borderwidth)
        pygame.draw.line(self.surf, self.bordercolor, (0, self.hA), (self.width, self.hA), self.borderwidth)
        pygame.draw.line(self.surf, self.bordercolor, (0, self.hB), (self.width, self.hB), self.borderwidth)
        self.screen.blit(self.surf, self.rect.topleft)
        



def main():
    #size = (1024, 600)
    graphfrac = 0.80
    pygame.init()
    pygame.font.init()
    pygame.display.set_caption("splitvent")
    screen = pygame.display.set_mode()
    size = screen.get_rect().size
    width,height = size
    fontsize = int(height / 32)
    linewidth = int(height / 200)
    bg = pygame.Surface(size)
    bg.fill(pygame.Color('#000000'))
    font = pygame.font.SysFont("menlottc", 30)
    print(font)
    n = 0
    running = True
    times = deque(maxlen=10)
    times.append(0.0)
    datapoints = deque(maxlen=width)
    textMargin = width * 0.75
    flowText = TextRectRenderer(screen, pygame.Rect(textMargin,0,width,height/2), "VTe", "mL", borderwidth=linewidth)
    while running:
        times.append(time.time())
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
              running = false
            elif event.type == pygame.KEYDOWN and event.key in [pygame.K_ESCAPE, pygame.K_Q]:
              running = false
        screen.blit(bg, (0,0))
        x = (n % 120) / 120.0
        datavalue = math.sin(2 * math.pi * x)
        datapoints.append(datavalue)
        y0 = height / 2
        pointlist = list((n,y+y0) for n,y in enumerate(datapoints))
        if len(datapoints) > 2:
            draw_graph(screen, (0,30,textMargin,(height/2)-30), datapoints, (-1.0,1.0), [], cyan, linewidth)
            #pygame.draw.lines(screen, (127,255,255), False, pointlist, 3)
        fps = (len(times) - 1) / (times[-1] - times[0])
        textsurf = font.render(
            "{:4.0f} fps n={:10d}  {:10.2f}"
                .format(fps, n, datavalue),
            True,
            (255,255,255),
            (0,0,0)
        )
        screen.blit(textsurf, (0,0))
        flowText.render("{:5.2f}".format(datavalue))
        pygame.display.update()
        n = n + 1
    pygame.quit()


if __name__=="__main__":
    main()
