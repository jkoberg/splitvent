
import time, math
from collections import deque

import pygame
from pygame.locals import *

cyan = (127,255,223)
yellow = (255, 255, 127)
green = (64,255,64)
border = (95,63,63)
black = (0,0,0)


class GraphRenderer(object):
    def __init__(self, screen, rect, color, width=3, reflines=[], bordercolor=border, borderwidth=3):
        self.screen = screen
        self.x0, self.y0, self.width, self.height = rect
        self.rect = rect
        self.color = color
        self.linewidth = width
        self.reflines = reflines
        self.bordercolor = bordercolor
        self.borderwidth = borderwidth
        self.rangefont = pygame.font.SysFont("menlottc", int(self.height * 0.1))

    def render_bg(self, bgsurf):
        pass
        #pygame.draw.rect(bgsurf, self.bordercolor, self.rect, self.borderwidth)

    def scale_values(self, values, yrange):
        ymin, ymax = yrange
        numvals = float(len(values))
        yscale = ymax - ymin if ymin != ymax else 1.0
        for n,v in enumerate(values):
            x = self.x0 + ((n / numvals) * self.width)
            y = self.y0 + self.height - (((v - ymin)/yscale) * self.height)
            yield (x, y)

    def render(self, idx, values, yrange=None):
        if yrange is None:
            yrange = (min(values), max(values))
        pts = list(self.scale_values(values, yrange))
        prefix = pts[:idx+1]
        suffix = pts[idx+1:]
        ymintxt = self.rangefont.render("   " + str(yrange[0]), True, self.bordercolor, black)
        self.screen.blit(ymintxt, ymintxt.get_rect(topleft=self.rect.bottomleft))
        ymaxtxt = self.rangefont.render("   " + str(yrange[1]), True, self.bordercolor, black)
        self.screen.blit(ymaxtxt, ymaxtxt.get_rect(bottomleft=self.rect.topleft))

        if len(prefix) > 2:
            pygame.draw.lines(self.screen, self.color, False, prefix, self.linewidth)
        if len(suffix) > 2:
            pygame.draw.lines(self.screen, self.color, False, suffix, self.linewidth)


class TextRectRenderer(object):
    def __init__(self, screen, rect,  header, unit, fontcolor=(255,255,255), bordercolor=border, borderwidth=3, bgcolor=(0,0,0)):
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
        self.L1 = (int(self.width * 0.05), int(self.height/8.0))
        self.AC2 = (rect.left + int(self.width / 2.0), rect.top + int(self.height/2.0))
        self.C3 = (int(self.width / 2.0), int(6.0*self.height/8.0))
        self.headerrect = self.headertxt.get_rect(midleft=self.L1)
        self.unitrect = self.unittxt.get_rect(center=self.C3)

    def render_bg(self, bgsurf):
        self.surf.fill(self.bgcolor)
        self.surf.blit(self.headertxt, self.headerrect)
        self.surf.blit(self.unittxt, self.unitrect)
        pygame.draw.rect(self.surf, self.bordercolor, self.relrect, self.borderwidth)
        #pygame.draw.line(self.surf, self.bordercolor, (0, self.hA), (self.width, self.hA), self.borderwidth)
        #pygame.draw.line(self.surf, self.bordercolor, (0, self.hB), (self.width, self.hB), self.borderwidth)
        bgsurf.blit(self.surf, self.rect.topleft)

    def render(self, value):
        value = self.largefont.render(str(value), True, self.fontcolor, self.bgcolor)
        self.screen.blit(value, value.get_rect(center=self.AC2))

def main():
    print("splitvent monitoring by Joe Koberg et al, http://github.com/jkoberg/splitvent")

    reqsize = (1024, 600)

    pygame.init()
    pygame.display.set_caption("splitvent")
    screen = pygame.display.set_mode(reqsize)
    size = screen.get_rect().size
    width, height = size

    pygame.font.init()
    font = pygame.font.SysFont("menlottc", 30)

    linewidth = int(height / 200)

    #fpstimes = deque(maxlen=10)
    #fpstimes.append(0.0)

    datalen = 1233
    datapoints = [0.0] * datalen

    datalen2 = 300
    datapoints2 = [0.0] * datalen2

    wstep = int(width / 12.)

    graphWidth = wstep * 9
    textWidth = wstep * 3

    hstep = int(height / 12.)

    flowGraph =  GraphRenderer(screen,    pygame.Rect(0, hstep*1,           graphWidth, hstep*4), green, linewidth)
    volGraph =   GraphRenderer(screen,    pygame.Rect(0, hstep*7,           graphWidth, hstep*4), cyan, linewidth)

    flowText =   TextRectRenderer(screen, pygame.Rect(graphWidth, 0,        textWidth, hstep*4), "RR", "mL",     fontcolor=green, borderwidth=linewidth)
    volumeText = TextRectRenderer(screen, pygame.Rect(graphWidth, hstep*4,  textWidth, hstep*4), "VTe", "b/min", fontcolor=cyan,  borderwidth=linewidth)
    vtitext =    TextRectRenderer(screen, pygame.Rect(graphWidth, hstep*8,  textWidth, hstep*2), "VTi", "mL",    fontcolor=cyan,  borderwidth=linewidth)
    mvetext =    TextRectRenderer(screen, pygame.Rect(graphWidth, hstep*10, textWidth, hstep*2), "MVe", "L/min", fontcolor=cyan,  borderwidth=linewidth)

    bg = pygame.Surface(size)
    bg.fill(pygame.Color('#000000'))

    pygame.draw.line(bg, border, (0, hstep*6), (width, hstep*6), linewidth)

    flowGraph.render_bg(bg)
    volGraph.render_bg(bg)
    flowText.render_bg(bg)
    volumeText.render_bg(bg)
    vtitext.render_bg(bg)
    mvetext.render_bg(bg)

    n = 0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
              running = False
            elif event.type == pygame.KEYDOWN and event.key in [pygame.K_ESCAPE, pygame.K_q]:
              running = False

        screen.blit(bg, (0,0))

        #fpstimes.append(time.time())
        #fps = (len(fpstimes) - 1) / (fpstimes[-1] - fpstimes[0])
        #textsurf = font.render(
        #    "{:4.0f} fps n={:10d}".format(fps, n),
        #    True,
        #    (255,255,255),
        #    (0,0,0)
        #)
        #screen.blit(textsurf, (0,0))

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
