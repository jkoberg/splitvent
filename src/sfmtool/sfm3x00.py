
from fcntl import ioctl
import struct, time, collections, shutil


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
        self._device = open('/dev/i2c-{0}'.format(bus), 'r+b', buffering=0)
        self._select_device(self.address)
        self.offset = self.read_offset()
        self.scale = self.read_scale()
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
        return (value - self.offset) / float(self.scale)
    
    def readings(self, dwell=0.010):
        self.start_sensor()
        time.sleep(0.100)
        self.read_value()
        last_t = time.time()
        time.sleep(dwell)
        t0 = time.time()        
        n = 0 
        while True:
            value = self.read_value()
            t = time.time()
            deltaT = t - last_t
            slm = self.scale_value(value)
            yield (n, t, deltaT, slm)
            n = n + 1
            t_next = (n * dwell) + t0
            t_sleep = t_next - t
            last_t = t
            time.sleep(max(0,t_sleep))
            
            



VOL_L_MIN = -1.0
VOL_L_MAX = 5.0

FLOW_SLM_MIN = -75.0
FLOW_SLM_MAX = 75.0

def pos_raw(vmin, vmax, width, val, refval=0.0, mark="#"):
    "Yield a string that represents a gauge, with a marker at a positions corresponding to val"
    scaled = max(0,min(width-1, int((val - vmin) * (width / (vmax - vmin))) ))
    scaled0 = max(0, min(width-1, int((refval - vmin) * (width / (vmax - vmin))) ))
    pstr = [u" "] * width
    pstr[scaled0] = u"."
    #pstr[0] = u"\u2591"
    #pstr[width - 1] = u"\u2591"
    pstr[scaled] = u"\u2588"
    return u"\x1b[37;44;1m" + u"".join(pstr) + u"\x1b[0m"

def pos_slm(val, width=40):
    "format slm gauge string"
    return pos_raw(FLOW_SLM_MIN, FLOW_SLM_MAX, width, val)

def pos_l(val, width=40):
    "format volume gauge string"
    return pos_raw(VOL_L_MIN, VOL_L_MAX, width, val)
        
        
class FlowPrinter(object):
    "Consume the readings from a SFM3x00, accumulate volume, and print"
    def __init__(self, sensor):
        self.sensor = sensor
        
    def print_header(self):
        s = self.sensor
        print("Serial Number: {}".format(s.serial_number))
        print("Value offset: {}".format(s.offset))
        print("Value scale: {}".format(s.scale))
        print("Starting flow measurements")
        
    def volume_loop(self, readings):
        total_volume = 0.0
        for r in readings:
            n, t, deltaT, slm = r
            sl = (deltaT / 60.0) * slm
            total_volume = total_volume + sl
            yield(n, t, deltaT, slm, sl, total_volume)
                
    def print_loop(self, volumes, skip=None):
        last_print_t = 0
        termsize = shutil.get_terminal_size()
        screenwidth, screenheight = termsize
        if skip is None:
            skip = int((12 / 0.010) / screenheight  )
        accum = collections.deque()
        for r in volumes:
            n, t, deltaT, slm, sl, total_volume = r
            accum.append(r)
            if len(accum) > skip:
                accum.popleft()
                if  n % skip == 0:
                    print_t = int(t)
                    t_str = time.strftime("%H:%M:%S", time.localtime(t)) + ("  n={:<8d}".format(n))   if print_t != last_print_t else ""
                    volume = sum(r[4] for r in accum)
                    timet = sum(r[2] for r in accum)
                    flow = volume / (timet / 60.0)
                    templatewidth = 48
                    colwidth = int((screenwidth - templatewidth) / 2)
                    yield u"{:>20}   {:>4.0f} slm   {}   {}   {:>5.0f} ml".format(
                        t_str,
                        flow,
                        pos_slm(flow, colwidth),
                        pos_l(total_volume, colwidth),
                        total_volume*1000
                        )
                    last_print_t = print_t
             

def main():
    with SFM3x00() as s:
        f = FlowPrinter(s)
        f.print_header()
        for line in f.print_loop(f.volume_loop(s.readings())):
            print(line)
        
        
        
    

if __name__ == "__main__":
    main()
        
        
        
        

        
        
