


import time, math, argparse, json, queue
import multiprocessing as mp

import numpy as np

from sfm3x00 import *
from HoneywellSSC import *
from calculations import *



try:
    from shutil import get_terminal_size
except:
    print("Assuming 80 x 24 terminal size. Use Python 3 for auto-detection of window size")
    def get_terminal_size():
        return (80, 24)



ANSI_WHITE_ON_BLUE = u"\x1b[37;44;1m"
ANSI_RESET_ATTRIBUTES = u"\x1b[0m"

def pos_raw(vmin, vmax, width, val, refval=0.0, mark=u"\u2588"):
    "Yield a string that represents a gauge, with a marker at a positions corresponding to val"
    scalefactor = width / (vmax - vmin)
    scaled = max(0, min(width-1, int((val - vmin) * scalefactor) ))
    scaled0 = max(0, min(width-1, int((refval - vmin) * scalefactor) ))
    pstr = [u" "] * width
    pstr[scaled0] = u"."
    pstr[scaled] = mark
    return ANSI_WHITE_ON_BLUE + u"".join(pstr) + ANSI_RESET_ATTRIBUTES



FLOW_SLM_MIN = -75.0
FLOW_SLM_MAX = 75.0

def pos_slm(val, width=40):
    "format slm gauge string"
    return pos_raw(FLOW_SLM_MIN, FLOW_SLM_MAX, width, val)


VOL_ML_MIN = -1000.0
VOL_ML_MAX = 5000.0

def pos_ml(val, width=40):
    "format volume gauge string"
    return pos_raw(VOL_ML_MIN, VOL_ML_MAX, width, val)



def print_header(s):
    print("Serial Number: {}".format(s.serial_number))
    print("Value offset: {}".format(s.offset))
    print("Value scale: {}".format(s.scale))
    print("Starting flow measurements")


def format_integrated(integratedReadings, sr=100.0, display_duration=12.0, skip=None):
    last_print_t = 0
    last_n = 0
    v_error = 0.0
    screenwidth, screenheight = get_terminal_size()
    if skip is None:
        skip = int((display_duration * sr) / screenheight)
    print("Formatter, sr={}, dur={}, skip={}".format(sr, display_duration, skip))
    accum = collections.deque(maxlen=skip)
    statsaccum = collections.deque(maxlen=int(sr*display_duration*2))
    veaccum = collections.deque(maxlen=3)
    for r in integratedReadings:
        accum.append(r)
        statsaccum.append(r.V)
        if len(accum) == skip:
            if  r.n % skip == 0:
                v_error = v_error - (0.1 * (v_error-min(statsaccum)))
                tidal_str = "VTi:     ml, VTe:     ml, RR:     b/min, MVe:      l/m"
                try:
                    if len(statsaccum) > 18:
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
                            tidal_str = "VTi:{:>4.0f} ml, VTe:{:>4.0f} ml, RR:{:4.1f} b/min, MVe:{:5.1f} l/m".format(VTi, VTe, rate[-1], mve)
                except:
                    pass
                print_t = int(r.t)
                if(print_t != last_print_t):
                    t_str = "{}  n={:<8d}".format(time.strftime("%H:%M:%S", time.localtime(r.t)), r.n-last_n)

                    last_n = r.n
                else:
                    t_str = ""
                volume = sum(r.dV for r in accum)
                timet = sum(r.dt for r in accum)
                flow = 0 if timet == 0 else (volume / (timet / 60.0)) / 1000
                templatewidth = 48 + len(tidal_str) +1
                colwidth = int((screenwidth - templatewidth) / 2)
                yield u"{:>20}   {:>4.0f} slm   {}   {}   {:>5.0f} ml {:11}".format(
                    t_str,
                    flow,
                    pos_slm(flow, colwidth),
                    pos_ml(r.V-v_error, colwidth),
                    r.V-v_error,
                    tidal_str
                )
                last_print_t = print_t




def parseArgs():
    parser = argparse.ArgumentParser(description='Read data from Sensirion SFM3x00 sensor over I2C.')

    parser.add_argument("--fake", dest='sensor_class',
                        action='store_const', const=FakeSensor, default=SFM3x00,
                        help='Use synthetic sensor data for demo')

    parser.add_argument("--samplerate", dest='sample_rate', type=float, default=100.0,
                        help='Flow measurement sampling rate')

    parser.add_argument("--duration", dest='display_duration', type=float, default=15.0,
                        help='number of seconds of readings to display')

    return parser.parse_args()


def main():
    args = parseArgs()

    with args.sensor_class() as s:
        print_header(s)
        readings = s.readings()
        timed = sample_clock(readings, args.sample_rate)
        integrated = integrate_readings(timed, args.sample_rate)
        formatted = format_integrated(integrated, args.sample_rate, args.display_duration)
        for line in formatted:
            print(line)



if __name__ == "__main__":
    main()
