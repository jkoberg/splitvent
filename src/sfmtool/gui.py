
import time, math, argparse
from collections import deque, namedtuple
import pygame
from pygame.locals import *
import numpy as np
import biopeaks.resp

from sfm3x00 import *

cyan = (127,255,223)
yellow = (255, 255, 127)
green = (64,255,64)
border = (95,63,63)
black = (0,0,0)


class GraphRenderer(object):
    def __init__(self, rect, color, width=3, reflines=[], bordercolor=border, borderwidth=3):
        self.x0, self.y0, self.width, self.height = rect
        self.rect = rect
        self.color = color
        self.linewidth = width
        self.reflines = reflines
        self.bordercolor = bordercolor
        self.borderwidth = borderwidth
        self.rangefont = pygame.font.SysFont("menlottc", int(self.height * 0.1))
        self.yrange = None

    def render_bg(self, surf):
        if self.yrange is not None:
            ymintxt = self.rangefont.render(" {:<12.2f}".format(self.yrange[0]), True, self.bordercolor, black)
            surf.blit(ymintxt, ymintxt.get_rect(topleft=self.rect.bottomleft))
            ymaxtxt = self.rangefont.render(" {:<12.2f}".format(self.yrange[1]), True, self.bordercolor, black)
            surf.blit(ymaxtxt, ymaxtxt.get_rect(bottomleft=self.rect.topleft))
            #pygame.draw.rect(bgsurf, self.bordercolor, self.rect, self.borderwidth)

    def scale_values(self, values):
        ymin, ymax = self.yrange
        numvals = float(len(values))
        yscale = ymax - ymin if ymin != ymax else 1.0
        for n,v in enumerate(values):
            x = self.x0 + ((n / numvals) * self.width)
            y = self.y0 + self.height - (((v - ymin)/yscale) * self.height)
            yield (x, y)

    def render(self, surf, idx, values, yrange=None):
        self.yrange = (min(values), max(values)) if yrange is None else yrange
        pts = list(self.scale_values(values))
        prefix = pts[:idx+1]
        suffix = pts[idx+1:]
        if len(prefix) > 2:
            pygame.draw.lines(surf, self.color, False, prefix, self.linewidth)
        if len(suffix) > 2:
            pygame.draw.lines(surf, self.color, False, suffix, self.linewidth)


class TextRectRenderer(object):
    def __init__(self, rect,  header, unit, fontcolor=(255,255,255), bordercolor=border, borderwidth=3, bgcolor=(0,0,0)):
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

    def render(self, surf, value):
        value = self.largefont.render(str(value), True, self.fontcolor, self.bgcolor)
        surf.blit(value, value.get_rect(center=self.AC2))



TidalData = namedtuple("TidalData", ["VTi", "VTe", "RR", "MVe"])

def format_gui_totalized(totalizedReadings, sr, datalen):
    v_error = 0.0
    print("Formatter, sr={}, datalen={}".format(sr, datalen))
    statsaccum = deque(maxlen=datalen)
    veaccum = deque(maxlen=3)
    for r in totalizedReadings:
        statsaccum.append(r.V)
        v_error = v_error - (0.01 * (v_error-min(statsaccum)))
        tidal_data = TidalData(0.0, 0.0, 0.0, 0.0)
        try:
            signal = np.array(statsaccum)
            resp_extrema = biopeaks.resp.resp_extrema(signal, sr)
            sigs = signal[resp_extrema]
            if len(resp_extrema) > 4:
                if sigs[-1] < sigs[-2]:
                    VTi = sigs[-2] - sigs[-3]
                    VTe = sigs[-2] - sigs[-1]
                else:
                    VTe = sigs[-3] - sigs[-2]
                    VTi = sigs[-1] - sigs[-2]
                veaccum.append(VTe)
                period, rate, tidalAmp = biopeaks.resp.resp_stats(resp_extrema, signal, sr)
                avgVTe = sum(veaccum)/len(veaccum)
                mve = (rate[-1] * avgVTe)/1000.0
                tidal_data = TidalData(VTi, VTe, rate[-1], mve)
        except:
            pass
        yield (r.slm, r.V-v_error, tidal_data)


def parseArgs():
    parser = argparse.ArgumentParser(description='Read data from Sensirion SFM3x00 sensor over I2C.')

    parser.add_argument("--fake", dest='sensor_class',
                        action='store_const', const=FakeSensor, default=SFM3x00,
                        help='Use synthetic sensor data for demo')

    parser.add_argument("--samplerate", dest='sample_rate', type=float, default=30.0,
                        help='Flow measurement sampling rate')

    parser.add_argument("--duration", dest='display_duration', type=float, default=15.0,
                        help='number of seconds of readings to display')

    return parser.parse_args()


def main():
    print("splitvent monitoring by Joe Koberg et al, http://github.com/jkoberg/splitvent")
    args = parseArgs()

    reqsize = (1024, 600)
    pygame.init()

    pygame.display.set_caption("splitvent")
    screen = pygame.display.set_mode(reqsize)
    size = screen.get_rect().size
    width, height = size

    pygame.font.init()
    font = pygame.font.SysFont("menlottc", 30)

    linewidth = int(height / 200)

    fpstimes = deque(maxlen=10)
    fpstimes.append(0.0)

    datalen = int(args.sample_rate * args.display_duration)
    flowPoints = [0.0] * datalen
    volPoints = [0.0] * datalen

    wstep = int(width / 12.)

    graphWidth = wstep * 9
    textWidth = wstep * 3

    hstep = int(height / 12.)

    flowGraph =  GraphRenderer(pygame.Rect(0, hstep*1,           graphWidth, hstep*4), green, linewidth)
    volGraph =   GraphRenderer(pygame.Rect(0, hstep*7,           graphWidth, hstep*4), cyan, linewidth)

    rrText =     TextRectRenderer(pygame.Rect(graphWidth, 0,        textWidth, hstep*4), "RR", "b/min",     fontcolor=green, borderwidth=linewidth)
    vteText = TextRectRenderer(pygame.Rect(graphWidth, hstep*4,  textWidth, hstep*4), "VTe", "ml", fontcolor=cyan,  borderwidth=linewidth)
    vtitext =    TextRectRenderer(pygame.Rect(graphWidth, hstep*8,  textWidth, hstep*2), "VTi", "ml",    fontcolor=cyan,  borderwidth=linewidth)
    mvetext =    TextRectRenderer(pygame.Rect(graphWidth, hstep*10, textWidth, hstep*2), "MVe", "l/min", fontcolor=cyan,  borderwidth=linewidth)

    bg = pygame.Surface(size)

    pygame.draw.line(bg, border, (0, hstep*6), (width, hstep*6), linewidth)

    bg.fill(pygame.Color('#000000'))
    flowGraph.render_bg(bg)
    volGraph.render_bg(bg)
    rrText.render_bg(bg)
    vteText.render_bg(bg)
    vtitext.render_bg(bg)
    mvetext.render_bg(bg)

    currentbg = bg

    lastTidal = None
    with args.sensor_class() as s:
        print_header(s)
        readings = s.readings()
        timed = sample_clock(readings, args.sample_rate)
        totalized = totalize_readings(timed)
        formatted = format_gui_totalized(totalized, args.sample_rate, 2*datalen)
        running = True
        n = 0
        for (slm, V, tidal) in formatted:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key in [pygame.K_ESCAPE, pygame.K_q]:
                    running = False
            if not running:
                break

            screen.blit(currentbg, (0,0))

            fpstimes.append(time.time())

            idx = n % datalen
            flowPoints[idx] = slm
            if len(flowPoints) > 2:
                flowGraph.render(screen, idx, flowPoints)

            volPoints[idx] = V
            if len(volPoints) > 2:
                volGraph.render(screen, idx, volPoints)

            if tidal != lastTidal:
                currentbg = bg.copy()
                fps = (len(fpstimes) - 1) / (fpstimes[-1] - fpstimes[0])
                textsurf = font.render(
                    "{:4.0f} fps n={:10d}".format(fps, n),
                    True,
                    (255,255,255),
                    (0,0,0)
                )
                currentbg.blit(textsurf, (0,0))
                flowGraph.render_bg(currentbg)
                volGraph.render_bg(currentbg)
                rrText.render(currentbg, "{:5.1f}".format(tidal.RR))
                vteText.render(currentbg,"{:5.0f}".format(tidal.VTe))
                vtitext.render(currentbg, "{:5.0f}".format(tidal.VTi))
                mvetext.render(currentbg, "{:5.1f}".format(tidal.MVe))

            pygame.display.update()
            n = n + 1
        print("Exiting normally.")
        pygame.quit()


if __name__=="__main__":
    main()
