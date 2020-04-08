
import time, math, json, queue, json
from collections import deque, namedtuple
import numpy as np
import biopeaks.resp
import scipy.signal


class CircularBuffer(object):
    def __init__(self, n, dtype=np.float32):
        self.arr = np.zeros(n, dtype=dtype)
        self.idx = 0
        self.full = False

    def append(self, v):
        self.arr[self.idx] = v
        newidx = self.idx + 1
        if not self.full and newidx == self.arr.size:
            self.full = True
        self.idx = newidx % self.arr.size

    def ordered(self):
        return np.roll(self.arr, -self.idx)




FlowPressureReading = namedtuple("FlowPressureReading", ["slm", "cmH2O"])

def combined_readings(flowClass, pressureClass):
    with flowClass() as s:
        with pressureClass() as p:
            s.prepare()
            p.prepare()
            while True:
                slm = s.read_scaled()
                cmH2O = p.read_scaled()
                yield FlowPressureReading(slm, cmH2O)


def clocked_from_file(filename, sr=None, clock=time.time, sleep=time.sleep):
    print("Readings from file {}".format(filename))
    with open(filename, "r") as f:
        t0 = clock()
        t = t0
        lastt = None
        n = 0
        for line in f:
            js = json.loads(line)
            tLine = js.t + t0
            sleep(max(0, tLine - t))
            if(lastt):
                deltaT = t - lastt
                yield TReading(n, t, deltaT, FlowPressureReading(js.slm, js.cmH2O))
                n = n + 1
            lastt = t
            t = clock()


TReading = namedtuple("TReading", ["n", "t", "dT", "value"])

def clocked(valueGenerator, sr, clock=time.time, sleep=time.sleep):
    """ Generate values at a fixed rate

    :param valueGenerator: The underlying generator to obtain values from
    :param sr: The sampling rate in samples per second
    :param clock: A function that returns the current time in seconds
    :param sleep: A function that sleeps (blocks) for a given time in seconds
    :return: A generator returning TReading tuples of (n, t, dT, value)
    """
    print("Clocked, sr={}".format(sr))
    t0 = clock()
    last_t = t0 - (1.0/sr)
    n = 0
    for v in valueGenerator:
        t = clock()
        deltaT = t - last_t
        yield TReading(n, t, deltaT, v)
        n = n + 1
        last_t = t
        t_sleep = max(0, ((n/sr) + t0) - t)
        sleep(t_sleep)




def makefilter(sr, taps=23):
    """Return an array of filter coefficients for a low-pass FIR filter at 3Hz"""
    return scipy.signal.firwin2(taps, [0, 3, 6, sr/2], [1, 1, 0.0001, 0.0001], window="hamming", fs=sr)

IntegratedVolume = namedtuple("IntegratedVolume", ["n", "t", "dT", "slm", "cmH2O", "dV", "V"])

def integrate_readings(timedReadings, sr):
    V = 0.0
    last_filtered_slm = 0.0
    taps = makefilter(sr)
    buffer = deque(maxlen=taps.size)
    fbuf = CircularBuffer(taps.size)
    coincident_idx = taps.size // 2
    for tup in timedReadings:
        buffer.append(tup)
        fbuf.append(tup.value.slm)
        if fbuf.full:
            filtered_slm = (taps * fbuf.ordered()).sum()
            if last_filtered_slm < 0 <= filtered_slm:
                V = 0.0
            last_filtered_slm = filtered_slm
            (n, t, dT, (slm, cmH2O)) = buffer[coincident_idx]
            dV = (dT * slm * 1000.0) / 60.0
            V = V + dV
            yield IntegratedVolume(n, t, dT, slm, cmH2O, dV, V)

VolumePressureReading = namedtuple("VolumePressureReading", ["V", "cmH2O"])

def stream_readings(flowClass, pressureClass, samplerate, displayQueue, tidalCalcQueue, finishq):
    combinedvals = combined_readings(flowClass, pressureClass)
    clockedvals = clocked(combinedvals, samplerate)
    integratedvals = integrate_readings(clockedvals, samplerate)
    for r in integratedvals:
        displayQueue.put(r)
        tidalCalcQueue.put(VolumePressureReading(r.V, r.cmH2O))
        if not finishq.empty():
            print("Exiting streaming process")
            return


def receive_readings(q):
    """Receive batches of values from a Queue"""
    try:
        while True:
            rs = [q.get(timeout=3.0)]
            while not q.empty():
                rs.append(q.get())
            yield rs
    except queue.Empty as ex:
        print("ERROR: Failed to get readings from background process.")


TidalData = namedtuple("TidalData", ["VTi", "VTe", "RR", "MVe", "PPk", "PEEP"])

def tidalcalcs(statslen, sample_rate, inputq, finishq, outputq):
    volume_signal = CircularBuffer(statslen)
    pressure_signal = CircularBuffer(statslen)
    veaccum = CircularBuffer(3)
    for inputs in receive_readings(inputq):
        for i in inputs:
            volume_signal.append(i.V)
            pressure_signal.append(i.cmH2O)
        try:
            vsig = volume_signal.ordered()
            resp_extrema = biopeaks.resp.resp_extrema(vsig, sample_rate)
            sigs = vsig[resp_extrema]
            if len(resp_extrema) > 4:
                if sigs[-1] < sigs[-2]:
                    VTi = sigs[-2] - sigs[-3]
                    VTe = sigs[-2] - sigs[-1]
                else:
                    VTe = sigs[-3] - sigs[-2]
                    VTi = sigs[-1] - sigs[-2]
                veaccum.append(VTe)
                period, rate, tidalAmp = biopeaks.resp.resp_stats(resp_extrema, vsig, sample_rate)
                avgVTe = veaccum.arr.sum() / veaccum.arr.size
                mve = (rate[-1] * avgVTe)/1000.0
                tidal = TidalData(VTi, VTe, rate[-1], mve, pressure_signal.arr.max(), pressure_signal.arr.min())
                outputq.put(tidal)
        except:
            print("Warning: tidal failed")
        if not finishq.empty():
            return
        time.sleep(0.5)
