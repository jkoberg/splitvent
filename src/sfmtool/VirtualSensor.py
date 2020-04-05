

import time, math

class FakeFlow(object):
    def __init__(self, min=-30.0, max=30.0, freq=1./3.):
        self.min = min
        self.range = max - min
        self.freq = freq

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def prepare(self):
        pass

    def read_scaled(self):
        v = (time.time() % 3.0) * (2 * math.pi) * self.freq
        r = (math.sin(v) + 1.0) * 0.5 * self.range
        return  r + self.min


class FakePressure(object):
    def __init__(self, min=2, max=20, freq=1./3.):
        self.min = min
        self.range = max - min
        self.freq = freq

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def prepare(self):
        pass

    def read_scaled(self):
        v = (time.time() % 3.0) * (2 * math.pi) * self.freq
        r = (math.copysign(1, math.sin(v)) + 1.0) * 0.5 * self.range
        return  r + self.min
