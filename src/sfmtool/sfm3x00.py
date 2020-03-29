
from fcntl import ioctl
import math, struct, time, collections, argparse


try:
    from shutil import get_terminal_size
except:
    print("Assuming 80 x 24 terminal size. Use Python 3 for auto-detection of window size")
    def get_terminal_size():
        return (80, 24)

"""Pure-python interface for SFM3X00 mass flow sensors"""

I2C_SLAVE             = 0x0703  #  Linux Kernel Constant

CMD_START_FLOW =   struct.pack(">H", 0x1000)
CMD_START_TEMP =   struct.pack(">H", 0x1000)
CMD_RESET =        struct.pack(">H", 0x2000)
CMD_RD_SCALE =     struct.pack(">H", 0x30de)
CMD_RD_OFFSET =    struct.pack(">H", 0x30df)
CMD_RD_SERNUM_1 =  struct.pack(">H", 0x31ae)
CMD_RD_SERNUM_2 =  struct.pack(">H", 0x31af)
CMD_RD_ARTICLE_1 = struct.pack(">H", 0x31e3)
CMD_RD_ARTICLE_2 = struct.pack(">H", 0x31e4)

RASPI_DEFAULT_I2C_BUS = 1
SENSIRION_SFM3x00_I2C_ADDR = 0x40



SfmReading = collections.namedtuple("SfmReading", ["slm"])

TimedReading = collections.namedtuple("TimedReading", ["slm", "n", "t", "dt"])

TotalizedReading = collections.namedtuple("TotalizedReading", ["slm", "n", "t", "dt", "dV", "V"])

class SFM3x00(object):
    """Read Sensirion SFM3x00 sensor readings over I2C"""
    
    def __init__(self, bus=RASPI_DEFAULT_I2C_BUS, address=SENSIRION_SFM3x00_I2C_ADDR):
        self.address = address
        self._device = None
        if bus is not None:
            self.open(bus)
        
    def __del__(self):
        self.close()
        
    def open(self, bus):
        if self._device is not None:
            self.close()
        devicename = '/dev/i2c-{0}'.format(bus)
        try:
            self._device = open(devicename, 'r+b', buffering=0)
            print('Opened {} for device communications'.format(devicename))
        except IOError:
            print('Unable to open port {} for device communications'.format(devicename))
            print('Use the --fake flag to simulate a device for testing')
            raise
        self._select_device(self.address)
        self.offset = float(self.read_offset())
        self.scale = float(self.read_scale())
        self.serial_number = self.read_serial_number()
        
    def close(self):
        if self._device is not None:
            self._device.close()
            self._device = None
            self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def _select_device(self, addr):
        ioctl(self._device.fileno(), I2C_SLAVE, addr & 0x7F)
        
    def write_bytes(self, bytes):
        assert self._device is not None, 'Bus must be opened before operations are made against it!'
        return self._device.write(bytes)

    def read_bytes(self, number):
        assert self._device is not None, 'Bus must be opened before operations are made against it!'
        return self._device.read(number)
    
    def start_sensor(self):
        self.write_bytes(CMD_START_FLOW)
                         
    def read_value(self):
        bytes = self.read_bytes(3)
        return struct.unpack(">H", bytes[:2])[0]
                         
    def read_serial_number(self):
        self.write_bytes(CMD_RD_SERNUM_1)
        bytes = self.read_bytes(6)
        return struct.unpack(">I", bytes[0:2] + bytes[3:5])[0]

    def read_offset(self):
        self.write_bytes(CMD_RD_OFFSET)
        bytes = self.read_bytes(3)
        return struct.unpack(">H", bytes[:2])[0]
                         
    def read_scale(self):
        self.write_bytes(CMD_RD_SCALE)
        bytes = self.read_bytes(3)
        return struct.unpack(">H", bytes[:2])[0]
    
    def scale_value(self, value):
        return (value - self.offset) / self.scale

    def readings(self):
        self.start_sensor() 
        time.sleep(0.100)
        self.read_value() # throw away the first read value
        while True:
            value = self.read_value()
            slm = self.scale_value(value)
            yield SfmReading(slm)


class FakeSensor(object):
    offset = 0.0
    scale = 1.0
    serial_number = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def readings(self):
        n = 0
        while True:
            v = n / 800.0
            slm = 60 * math.sin(v * 2 * math.pi)
            yield SfmReading(slm)
            n = (n + 1) % 800


def sample_clock(valueGenerator, dwell=0.010, clock=time.time):
    last_t = clock()
    time.sleep(dwell)
    t0 = clock()
    n = 0
    for slm in valueGenerator:
        t = clock()
        deltaT = t - last_t
        yield TimedReading(slm.slm, n, t, deltaT)
        n = n + 1
        t_sleep = max(0, ((n * dwell) + t0) - t)
        last_t = t
        time.sleep(t_sleep)


def totalize_readings(timedReadings):
    V = 0.0
    for r in timedReadings:
        dV = (r.dt * r.slm) / 60.0
        V = V + dV
        yield TotalizedReading(r.slm, r.n, r.t, r.dt, dV, V)




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


VOL_L_MIN = -1.0
VOL_L_MAX = 5.0

def pos_l(val, width=40):
    "format volume gauge string"
    return pos_raw(VOL_L_MIN, VOL_L_MAX, width, val)



def print_header(s):
    print("Serial Number: {}".format(s.serial_number))
    print("Value offset: {}".format(s.offset))
    print("Value scale: {}".format(s.scale))
    print("Starting flow measurements")

        

def format_totalized(totalizedReadings, dwell=0.10, display_duration=12.0, skip=None):
    last_print_t = 0
    screenwidth, screenheight = get_terminal_size()
    if skip is None:
        skip = int((display_duration / dwell) / screenheight)
    accum = collections.deque()
    for r in totalizedReadings:
        accum.append(r)
        if len(accum) > skip:
            accum.popleft()
            if  r.n % skip == 0:
                print_t = int(r.t)
                t_str = ("{}  n={:<8d}".format(time.strftime("%H:%M:%S", time.localtime(r.t)), r.n)
                         if print_t != last_print_t
                         else "" )
                volume = sum(r.dV for r in accum)
                timet = sum(r.dt for r in accum)
                flow = 0 if timet == 0 else volume / (timet / 60.0)
                templatewidth = 48
                colwidth = int((screenwidth - templatewidth) / 2)
                yield u"{:>20}   {:>4.0f} slm   {}   {}   {:>5.0f} ml".format(
                    t_str,
                    flow,
                    pos_slm(flow, colwidth),
                    pos_l(r.V, colwidth),
                    r.V * 1000
                    )
                last_print_t = print_t
             

def main():
    parser = argparse.ArgumentParser(description='Read data from Sensirion SFM3x00 sensor over I2C.')

    parser.add_argument("--fake", dest='sensor_class',
                        action='store_const', const=FakeSensor, default=SFM3x00,
                        help='Use synthetic sensor data for demo')

    parser.add_argument("--samplerate", dest='sample_rate', type=float, default=100.0,
                        help='Flow measurement sampling rate')

    parser.add_argument("--duration", dest='display_duration', type=float, default=15.0,
                        help='number of seconds of readings to display')

    args = parser.parse_args()

    dwell = 1.0/args.sample_rate

    with args.sensor_class() as s:
        print_header(s)
        readings = s.readings()
        timed = sample_clock(readings, dwell)
        totalized = totalize_readings(timed)
        formatted = format_totalized(totalized, dwell, args.display_duration)
        for line in formatted:
            print(line)
        
        
        
    

if __name__ == "__main__":
    main()
        
        
        
        

        
        
