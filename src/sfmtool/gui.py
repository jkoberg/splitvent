
import time, math, argparse, json, queue
import multiprocessing as mp

import numpy as np

from sfm3x00 import *
from HoneywellSSC import *
from calculations import *
from VirtualSensor import *

print("splitvent monitoring system by Joe Koberg, March 2020.  https://github.com/jkoberg/splitvent")
print("This work is provided under a Creative Commons Share Alike 4.0 license.")

import pygame
from pygame.locals import *


yellow = (224, 224, 95)
cyan = (127,255,223)
yellow = (255, 255, 127)
green = (64,255,64)
border = (63,63,63)
black = (0,0,0)

FONT = "liberationsans"
ANTIALIAS = True

class GraphRenderer(object):
    def __init__(self, minyrange, rect, color, width=3, reflines=[0.0], bordercolor=border, borderwidth=3):
        self.x0, self.y0, self.width, self.height = rect
        self.rect = rect
        self.color = color
        self.linewidth = width
        self.reflines = reflines
        self.bordercolor = bordercolor
        self.borderwidth = borderwidth
        self.rangefont = pygame.font.SysFont(FONT, int(self.height * 0.1))
        self.yrange = minyrange
        self.minyrange = minyrange

    def render_bg(self, surf):
        return
        if self.yrange is not None:
            ymintxt = self.rangefont.render(" {:<12.2f}".format(self.yrange[0]), ANTIALIAS, self.bordercolor, black)
            surf.blit(ymintxt, ymintxt.get_rect(topleft=self.rect.bottomleft))
            ymaxtxt = self.rangefont.render(" {:<12.2f}".format(self.yrange[1]), ANTIALIAS, self.bordercolor, black)
            surf.blit(ymaxtxt, ymaxtxt.get_rect(bottomleft=self.rect.topleft))
            #pygame.draw.rect(bgsurf, self.bordercolor, self.rect, self.borderwidth)

    def scale_y(self, v, yrange):
        ymin, ymax = yrange
        yscale = ymax - ymin if ymin != ymax else 1.0
        yoffset = self.y0 + self.height
        return yoffset - (((v - ymin ) / yscale) * self.height)

    def scale_values(self, values, yrange):
        xstep = self.width / values.size
        xints = np.arange(0, self.width, xstep, dtype=np.float)[:values.size]
        xs = xints + self.x0
        ys = self.scale_y(values, yrange)
        return np.column_stack((xs, ys))

    def render(self, surf, idx, values, yrange=None):
        if yrange is None:
            vmin = min(self.minyrange[0], values.min())
            vmax = max(self.minyrange[1], values.max())
            yrange = (vmin, vmax)
        pts = self.scale_values(values, yrange)
        prefix = pts[:idx]
        suffix = pts[idx:]

        ymintxt = self.rangefont.render(" {:.2f}".format(yrange[0]), ANTIALIAS, self.bordercolor, black)
        surf.blit(ymintxt, ymintxt.get_rect(topleft=self.rect.bottomleft))

        ymaxtxt = self.rangefont.render(" {:.2f}".format(yrange[1]), ANTIALIAS, self.bordercolor, black)
        surf.blit(ymaxtxt, ymaxtxt.get_rect(bottomleft=self.rect.topleft))

        for refline in self.reflines:
            y = self.scale_y(refline, yrange)
            pygame.draw.line(surf, self.bordercolor, (0, y), (self.width, y), self.borderwidth)

        if prefix.size > 2:
            pygame.draw.lines(surf, self.color, False, prefix, self.linewidth)
        if suffix.size > 2:
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
        self.smallfont = pygame.font.SysFont(FONT, int(self.height * 0.15))
        self.largefont = pygame.font.SysFont(FONT, int(self.height * 0.30))
        self.headertxt = self.smallfont.render(header, ANTIALIAS,  fontcolor, bgcolor)
        self.unittxt = self.smallfont.render(unit, ANTIALIAS, fontcolor, bgcolor)
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
        value = self.largefont.render(str(value), ANTIALIAS, self.fontcolor, self.bgcolor)
        surf.blit(value, value.get_rect(center=self.AC2))



def parseArgs():
    parser = argparse.ArgumentParser(description='Read data from Sensirion SFM3x00 sensor over I2C.')

    parser.add_argument("--fake", dest='sensor_classes',
                        action='store_const', const=(FakeFlow, FakePressure), default=(SFM3x00, HoneywellSSC),
                        help='Use synthetic sensor data for demo')

    parser.add_argument("--samplerate", dest='sample_rate', type=float, default=50.0,
                        help='Flow measurement sampling rate')

    parser.add_argument("--duration", dest='display_duration', type=float, default=15.0,
                        help='number of seconds of readings to display')

    parser.add_argument("--log", dest='log_data', action='store_const', const=True, default=False,
                        help='Write data to logfile')

    parser.add_argument("--quiet", dest='quiet', action='store_const', const=True, default=False,
                        help="Don't update display")

    parser.add_argument("--width", dest='req_w', default=1280, type=int, help="Requested display width")

    parser.add_argument("--height", dest='req_h', default=720, type=int, help="Requested display height")

    parser.add_argument("--sscrange", dest='ssc_range_code', default='015PG', type=str, help="Honeywell SSC sensor range code")

    parser.add_argument("--sscxfer", dest='ssc_xfer_func', default='A', type=str, help="Honeywell SSC sensor transfer function code")

    return parser.parse_args()



def guiMain(args):
    pygame.display.set_caption("splitvent")
    screen = pygame.display.set_mode((args.req_w, args.req_h))
    size = screen.get_rect().size
    width, height = size

    pygame.font.init()
    font = pygame.font.SysFont(FONT, 30)

    datalen = int(args.sample_rate * args.display_duration)

    fpstimes = CircularBuffer(10)
    srtimes = CircularBuffer(int(args.sample_rate))
    flowPoints = CircularBuffer(datalen)
    volPoints = CircularBuffer(datalen)
    pressPoints = CircularBuffer(datalen)

    linewidth = int(height / 200.)
    wstep = int(width / 12.)
    hstep = int(height / 12.)
    graphWidth = wstep * 10
    textWidth = wstep * 2

    pressGraph = GraphRenderer((0, 35),      pygame.Rect(0, hstep*0.5,         graphWidth, hstep*3), yellow , linewidth)
    flowGraph =  GraphRenderer((-50, 50),    pygame.Rect(0, hstep*4.5,         graphWidth, hstep*3), green,   linewidth)
    volGraph =   GraphRenderer((-100, 1000), pygame.Rect(0, hstep*8.5,         graphWidth, hstep*3), cyan,    linewidth)

    pressTest =  TextRectRenderer(pygame.Rect(graphWidth, 0,          textWidth, hstep*2.5), "Ppk",  "cm H2O", fontcolor=yellow, borderwidth=linewidth)
    peepText =   TextRectRenderer(pygame.Rect(graphWidth, hstep*2.5,  textWidth, hstep*1.5), "PEEP", "cm H2O", fontcolor=yellow, borderwidth=linewidth)
    rrText =     TextRectRenderer(pygame.Rect(graphWidth, hstep*4,    textWidth, hstep*2.5), "RR",   "b/min",  fontcolor=green,  borderwidth=linewidth)
    vteText =    TextRectRenderer(pygame.Rect(graphWidth, hstep*6.5,  textWidth, hstep*2.5), "VTe",  "ml",     fontcolor=cyan,   borderwidth=linewidth)
    vtitext =    TextRectRenderer(pygame.Rect(graphWidth, hstep*9,    textWidth, hstep*1.5), "VTi",  "ml",     fontcolor=cyan,   borderwidth=linewidth)
    mvetext =    TextRectRenderer(pygame.Rect(graphWidth, hstep*10.5, textWidth, hstep*1.5), "MVe",  "l/min",  fontcolor=cyan,   borderwidth=linewidth)

    widgets = [
        pressGraph,
        flowGraph,
        volGraph,
        pressTest,
        peepText,
        rrText,
        vteText,
        vtitext,
        mvetext,
    ]

    #bg = pygame.Surface(size)
    #bg.fill(pygame.Color('#000000'))

    #pygame.draw.line(bg, border, (0, hstep*6), (graphWidth, hstep*6), linewidth)

    for widget in widgets:
        widget.render_bg(screen)

    #currentbg = bg
    #screen.blit(currentbg, (0,0))

    pygame.display.update()
    
    resultq = mp.Queue()
    tidalInputQueue = mp.Queue()
    tidalOutputQueue = mp.Queue()
    finishq = mp.Queue()

    flowClass, pressureClass = args.sensor_classes

    child1 = mp.Process(
        target = stream_readings,
        args = (flowClass, pressureClass, args.sample_rate, resultq, tidalInputQueue, finishq)
        )
    child1.start()

    child2 = mp.Process(
        target = tidalcalcs,
        args = (datalen*2, args.sample_rate, tidalInputQueue, finishq, tidalOutputQueue)
        )
    child2.start()

    try:
        print("Formatter, sr={}, datalen={}".format(args.sample_rate, datalen))
        if args.log_data:
            datestr = time.strftime("%Y%m%d_%H%M%S", time.localtime(time.time()))
            filename = "splitvent-{}hz-{}.log".format(int(args.sample_rate), datestr)
            logfile = open(filename, "w")
            print("logging to " + filename)
        else:
            logfile = None

        integrated_groups = receive_readings(resultq)

        keepRunning = True
        n = 0
        frames = 0
        t0 = None
        tidal = None
        for group in integrated_groups:
            for r in group:
                srtimes.append(r.t)
                if t0 is None:
                    t0 = r.t
                if logfile is not None:
                    logfile.write('{{"t":{:.6f}, "slm":{:.2f}, "cmH2O": {:.2f}}}\n'.format(r.t-t0, r.slm, r.cmH2O))
                flowPoints.append(r.slm)
                volPoints.append(r.V)
                pressPoints.append(r.cmH2O)
                n = n + 1

            while not tidalOutputQueue.empty():
                tidal = tidalOutputQueue.get()

            #screen.blit(currentbg, (0,0))
            for widget in widgets:
                widget.render_bg(screen)

            fpstimes.append(time.time())

            flowGraph.render(screen, flowPoints.idx, flowPoints.arr)
            volGraph.render(screen, volPoints.idx, volPoints.arr)
            pressGraph.render(screen, pressPoints.idx, pressPoints.arr)

            if tidal is not None:
                #currentbg = bg.copy()
                #fps = (len(fpstimes) - 1) / (fpstimes[-1] - fpstimes[0])
                #srcomputed = (len(srtimes) - 1) / (srtimes[-1] - srtimes[0])
                #fpsmsg = "{:4.0f} fps n={:10d} g={} sr={:.2f}".format(fps, n, len(group), srcomputed)
                #textsurf = font.render(
                #    fpsmsg,
                #    ANTIALIAS,
                #    (255,255,255),
                #    (0,0,0)
                #)
                #print(fpsmsg)
                #screen.blit(textsurf, (0,0))
                #flowGraph.render_bg(currentbg)
                #volGraph.render_bg(currentbg)
                pressTest.render(screen, "{:5.1f}".format(tidal.PPk))
                peepText.render(screen, "{:5.1f}".format(tidal.PEEP))
                rrText.render(screen, "{:5.1f}".format(tidal.RR))
                vteText.render(screen,"{:5.0f}".format(tidal.VTe))
                vtitext.render(screen, "{:5.0f}".format(tidal.VTi))
                mvetext.render(screen, "{:5.1f}".format(tidal.MVe))

            if not args.quiet:
                pygame.display.update()
                screen.fill(black)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    keepRunning = False
                elif event.type == pygame.KEYDOWN and event.key in [pygame.K_ESCAPE, pygame.K_q]:
                    keepRunning = False

            if not keepRunning:
                break

            frames = frames + 1
        print("Exiting normally.")
    finally:
        finishq.put("Finish")
        child1.join()
        child2.join()


if __name__=="__main__":
    try:
        pygame.init()
        guiMain(parseArgs())
    finally:
        pygame.quit()
