
import time, math
from collections import deque

import pygame
from pygame.locals import *

cyan = (127,255,223)
yellow = (255, 255, 127)



class GraphRenderer(object):
    def __init__(self, screen, rect, color, width=3, reflines=[]):
        self.screen = screen
        self.x0, self.y0, self.width, self.height = rect
        self.rect = rect
        self.color = color
        self.linewidth = width
        self.reflines = reflines

    def render_bg(self, bgsurf):
        pass

    def scale_values(self, values, yrange=None):
        if yrange is None:
            yrange = (min(values), max(values))
        ymin, ymax = yrange
        numvals = float(len(values))
        yscale = ymax - ymin if ymin != ymax else 1.0
        for n,v in enumerate(values):
            x = self.x0 + ((n / numvals) * self.width)
            y = self.y0 + self.height - (((v - ymin)/yscale) * self.height)
            yield (x, y)

    def render(self, idx, values, yrange=None):
        pts = list(self.scale_values(values, yrange))
        prefix = pts[:idx+1]
        suffix = pts[idx+1:]
        if len(prefix) > 2:
            pygame.draw.lines(self.screen, self.color, False, prefix, self.linewidth)
        if len(suffix) > 2:
            pygame.draw.lines(self.screen, self.color, False, suffix, self.linewidth)


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
        self.smallfont = pygame.font.SysFont("menlottc", int(self.height * 0.15))
        self.largefont = pygame.font.SysFont("menlottc", int(self.height * 0.25))
        self.headertxt = self.smallfont.render(header, True, fontcolor, bgcolor)
        self.unittxt = self.smallfont.render(unit, True, fontcolor, bgcolor)
        self.C1 = (int(self.width / 2.0), int(self.height/8.0))
        self.AC2 = (rect.left + int(self.width / 2.0), rect.top + int(self.height/2.0))
        self.C3 = (int(self.width / 2.0), int(6.0*self.height/8.0))
        self.headerrect = self.headertxt.get_rect(center=self.C1)
        self.unitrect = self.unittxt.get_rect(center=self.C3)

    def render_bg(self, bgsurf):
        self.surf.fill(self.bgcolor)
        self.surf.blit(self.headertxt, self.headerrect)
        self.surf.blit(self.unittxt, self.unitrect)
        pygame.draw.rect(self.surf, self.bordercolor, self.relrect, self.borderwidth)
        #pygame.draw.line(self.surf, self.bordercolor, (0, self.hA), (self.width, self.hA), self.borderwidth)
        pygame.draw.line(self.surf, self.bordercolor, (0, self.hB), (self.width, self.hB), self.borderwidth)
        bgsurf.blit(self.surf, self.rect.topleft)

    def render(self, value):
        value = self.largefont.render(str(value), True, self.fontcolor, self.bgcolor)
        self.screen.blit(value, value.get_rect(center=self.AC2))

def main():
    print("splitvent monitoring by Joe Koberg et al, http://github.com/jkoberg/splitvent")
    reqsize = (1024, 600)
    graphfrac = 0.80
    pygame.init()
    pygame.font.init()
    pygame.display.set_caption("splitvent")
    screen = pygame.display.set_mode(reqsize)
    size = screen.get_rect().size
    width,height = size
    fontsize = int(height / 32)
    linewidth = int(height / 200)
    font = pygame.font.SysFont("menlottc", 30)
    n = 0
    running = True
    times = deque(maxlen=10)
    times.append(0.0)
    datalen = 1233
    datalen2 = 300
    datapoints = [0.0] * datalen
    datapoints2 = [0.0] * datalen2
    textMargin = width * 0.75
    textWidth = width * 0.25
    flowText = TextRectRenderer(screen, pygame.Rect(textMargin,0,textWidth,height/2), "VTe", "mL", fontcolor=cyan, borderwidth=linewidth)
    volumeText = TextRectRenderer(screen, pygame.Rect(textMargin,height/2,textWidth,height/2), "RR", "b/min", fontcolor=yellow, borderwidth=linewidth)
    bg = pygame.Surface(size)
    bg.fill(pygame.Color('#000000'))
    flowText.render_bg(bg)
    volumeText.render_bg(bg)
    flowGraph = GraphRenderer(screen, pygame.Rect(0,30, textMargin,(height/2)-60), cyan, linewidth)
    volGraph = GraphRenderer(screen, pygame.Rect(0,(height/2)+30, textMargin,(height/2)-60), yellow, linewidth)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
              running = False
            elif event.type == pygame.KEYDOWN and event.key in [pygame.K_ESCAPE, pygame.K_q]:
              running = False

        screen.blit(bg, (0,0))

        times.append(time.time())
        fps = (len(times) - 1) / (times[-1] - times[0])
        textsurf = font.render(
            "{:4.0f} fps n={:10d}".format(fps, n),
            True,
            (255,255,255),
            (0,0,0)
        )
        screen.blit(textsurf, (0,0))

        x = (n % 120) / 120.0
        datavalue = math.sin(2 * math.pi * x)
        idx = n % datalen
        datapoints[idx] = datavalue
        if len(datapoints) > 2:
            flowGraph.render(idx, datapoints)
            #pygame.draw.lines(screen, (127,255,255), False, pointlist, 3)
        flowText.render("{:5.0f}".format(datavalue*1000))

        datavalue2 = math.cos(2 * math.pi * x)
        idx2 = n % datalen2
        datapoints2[idx2] = datavalue2
        if len(datapoints2) > 2:
            volGraph.render(idx2, datapoints2)
        volumeText.render("{:5.1f}".format(datavalue2*10))

        pygame.display.update()
        n = n + 1
    print("Exiting normally.")
    pygame.quit()


if __name__=="__main__":
    main()
