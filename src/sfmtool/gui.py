
import time, math, argparse, json, multiprocessing
import multiprocessing as mp
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
    def __init__(self, minyrange, rect, color, width=3, reflines=[0.0], bordercolor=border, borderwidth=3):
        self.x0, self.y0, self.width, self.height = rect
        self.rect = rect
        self.color = color
        self.linewidth = width
        self.reflines = reflines
        self.bordercolor = bordercolor
        self.borderwidth = borderwidth
        self.rangefont = pygame.font.SysFont("menlottc", int(self.height * 0.1))
        self.yrange = minyrange
        self.minyrange = minyrange

    def render_bg(self, surf):
        return
        if self.yrange is not None:
            ymintxt = self.rangefont.render(" {:<12.2f}".format(self.yrange[0]), True, self.bordercolor, black)
            surf.blit(ymintxt, ymintxt.get_rect(topleft=self.rect.bottomleft))
            ymaxtxt = self.rangefont.render(" {:<12.2f}".format(self.yrange[1]), True, self.bordercolor, black)
            surf.blit(ymaxtxt, ymaxtxt.get_rect(bottomleft=self.rect.topleft))
            #pygame.draw.rect(bgsurf, self.bordercolor, self.rect, self.borderwidth)

    def scale_values(self, values, yrange):
        xstep = self.width / values.size
        xints = np.arange(0, self.width, xstep)
        xs = xints + self.x0
        ymin, ymax = yrange
        yscale = ymax - ymin if ymin != ymax else 1.0
        yoffset = self.y0 + self.height
        ys = yoffset - (((values - ymin ) / yscale) * self.height)
        return np.column_stack((xs, ys))

    def scale_y(self, v, yrange):
        ymin, ymax = yrange
        yscale = ymax - ymin if ymin != ymax else 1.0
        return self.y0 + self.height - (((v - ymin) / yscale) * self.height)

    def render(self, surf, idx, values, yrange=None):
        if yrange is None:
            vmin = min(self.minyrange[0], values.min())
            vmax = max(self.minyrange[1], values.max())
            yrange = (vmin, vmax)
        pts = self.scale_values(values, yrange)
        prefix = pts[:idx+1]
        suffix = pts[idx+1:]

        ymintxt = self.rangefont.render(" {:.2f}".format(yrange[0]), False, self.bordercolor, black)
        surf.blit(ymintxt, ymintxt.get_rect(topleft=self.rect.bottomleft))
        ymaxtxt = self.rangefont.render(" {:.2f}".format(yrange[1]), False, self.bordercolor, black)
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
        value = self.largefont.render(str(value), False, self.fontcolor, self.bgcolor)
        surf.blit(value, value.get_rect(center=self.AC2))



TidalData = namedtuple("TidalData", ["VTi", "VTe", "RR", "MVe"])


def parseArgs():
    parser = argparse.ArgumentParser(description='Read data from Sensirion SFM3x00 sensor over I2C.')

    parser.add_argument("--fake", dest='sensor_class',
                        action='store_const', const=FakeSensor, default=SFM3x00,
                        help='Use synthetic sensor data for demo')

    parser.add_argument("--samplerate", dest='sample_rate', type=float, default=50.0,
                        help='Flow measurement sampling rate')

    parser.add_argument("--duration", dest='display_duration', type=float, default=15.0,
                        help='number of seconds of readings to display')

    parser.add_argument("--log", dest='log_data', action='store_const', const=True, default=False,
                        help='Write data to logfile')

    parser.add_argument("--quiet", dest='quiet', action='store_const', const=True, default=False,
                        help="Don't update display")

    return parser.parse_args()


def stream_readings(sensorclass, samplerate, resultq, finishq):
    with sensorclass() as s:
        readings = s.readings()
        for reading in sample_clock(readings, samplerate):
            resultq.put(reading)
            if not finishq.empty():
                break

def receive_readings(q):
    while True:
        rs = [q.get()]
        while not q.empty():
            rs.append(q.get())
        yield rs
    
 

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

    srtimes = deque(maxlen=int(args.sample_rate))
    srtimes.append(0.0)

    datalen = int(args.sample_rate * args.display_duration)
    flowPoints = np.zeros(datalen)
    volPoints = np.zeros(datalen)

    wstep = int(width / 12.)

    graphWidth = wstep * 9
    textWidth = wstep * 3

    hstep = int(height / 12.)

    flowGraph =  GraphRenderer((-50, 50), pygame.Rect(0, hstep*1,           graphWidth, hstep*4), green, linewidth)
    volGraph =   GraphRenderer((-100, 1000), pygame.Rect(0, hstep*7,           graphWidth, hstep*4), cyan, linewidth)

    rrText =     TextRectRenderer(pygame.Rect(graphWidth, 0,        textWidth, hstep*4), "RR", "b/min",     fontcolor=green, borderwidth=linewidth)
    vteText = TextRectRenderer(pygame.Rect(graphWidth, hstep*4,  textWidth, hstep*4), "VTe", "ml", fontcolor=cyan,  borderwidth=linewidth)
    vtitext =    TextRectRenderer(pygame.Rect(graphWidth, hstep*8,  textWidth, hstep*2), "VTi", "ml",    fontcolor=cyan,  borderwidth=linewidth)
    mvetext =    TextRectRenderer(pygame.Rect(graphWidth, hstep*10, textWidth, hstep*2), "MVe", "l/min", fontcolor=cyan,  borderwidth=linewidth)

    bg = pygame.Surface(size)
    bg.fill(pygame.Color('#000000'))

    pygame.draw.line(bg, border, (0, hstep*6), (width, hstep*6), linewidth)

    flowGraph.render_bg(bg)
    volGraph.render_bg(bg)
    rrText.render_bg(bg)
    vteText.render_bg(bg)
    vtitext.render_bg(bg)
    mvetext.render_bg(bg)

    currentbg = bg
    screen.blit(currentbg, (0,0))
    pygame.display.update()
    
    resultq = mp.Queue()
    finishq = mp.Queue()
    child = mp.Process(
        target = stream_readings,
        args = (args.sensor_class, args.sample_rate, resultq, finishq)
        )
    child.start()


    try: # with args.sensor_class() as s:
        print("Formatter, sr={}, datalen={}".format(args.sample_rate, datalen))
        #print_header(s)

        if args.log_data:
            datestr = time.strftime("%Y%m%d_%H%M%S", time.localtime(time.time()))
            filename = "splitvent-sn{}-{}hz-{}.log".format(str(s.serial_number), int(args.sample_rate), datestr)
            logfile = open(filename, "w")
            print("logging to " + filename)
        else:
            logfile = None

        #readings = s.readings()
        #timed = free_running(readings) 
        #timed = sample_clock(readings, args.sample_rate)

        timedgroups = receive_readings(resultq)
        #integrated = integrate_readings(timed, args.sample_rate)
        integrated_groups = integrate_reading_groups(timedgroups, args.sample_rate)
        running = True
        last_tidal_time = 0.0
        last_tidal = None
        n = 0
        frames = 0
        t0 = None
        print("Formatter, sr={}, datalen={}".format(args.sample_rate, datalen))
        statsaccum = np.zeros(datalen*2)
        veaccum = deque(maxlen=3)
        for group in integrated_groups:
            tidal = None
            for r in group:
                srtimes.append(r.t)
                if t0 is None:
                    t0 = r.t
                if logfile is not None:
                    logfile.write('{{"t":{:.6f}, "slm":{:.2f}}}\n'.format(r.t-t0, r.slm))
                statsaccum = np.roll(statsaccum, -1)
                statsaccum[-1] = r.V
                try:
                    if(r.n % args.sample_rate == 0): # compute tidal data once per second
                        signal = statsaccum # np.array(statsaccum)
                        resp_extrema = biopeaks.resp.resp_extrema(signal, args.sample_rate)
                        sigs = signal[resp_extrema]
                        if len(resp_extrema) > 4:
                            if sigs[-1] < sigs[-2]:
                                VTi = sigs[-2] - sigs[-3]
                                VTe = sigs[-2] - sigs[-1]
                            else:
                                VTe = sigs[-3] - sigs[-2]
                                VTi = sigs[-1] - sigs[-2]
                            veaccum.append(VTe)
                            period, rate, tidalAmp = biopeaks.resp.resp_stats(resp_extrema, signal, args.sample_rate)
                            avgVTe = sum(veaccum)/len(veaccum)
                            mve = (rate[-1] * avgVTe)/1000.0
                            tidal = TidalData(VTi, VTe, rate[-1], mve)
                except:
                    pass

                idx = n % datalen
                flowPoints[idx] = r.slm
                volPoints[idx] = r.V
                n = n + 1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key in [pygame.K_ESCAPE, pygame.K_q]:
                    running = False
            if not running:
                break

            screen.blit(currentbg, (0,0))

            fpstimes.append(time.time())

            if len(flowPoints) > 2:
                flowGraph.render(screen, idx, flowPoints)

            if len(volPoints) > 2:
                volGraph.render(screen, idx, volPoints)

            if tidal is not None: # and tidal != last_tidal and (r.t - last_tidal_time > 0.5) :
                last_tidal = tidal
                last_tidal_time = r.t
                currentbg = bg.copy()
                fps = (len(fpstimes) - 1) / (fpstimes[-1] - fpstimes[0])
                srcomputed = (len(srtimes) - 1) / (srtimes[-1] - srtimes[0])
                textsurf = font.render(
                    "{:4.0f} fps n={:10d} sr={:.2f}".format(fps, n, srcomputed),
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

            if not args.quiet:
                pygame.display.update()
            frames = frames + 1
        print("Exiting normally.")
        pygame.quit()
    finally:
        finishq.put("Finish")
        child.join()


if __name__=="__main__":
    main()
