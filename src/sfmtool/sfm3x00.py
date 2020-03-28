

from ctypes import c_uint8, c_uint16, c_uint32, cast, pointer, POINTER
from ctypes import create_string_buffer, Structure
from fcntl import ioctl
import struct, time


"""Pure-python interface for SFM3X00 mass flow sensors"""

# I2C C API constants (from linux kernel headers)
I2C_M_TEN             = 0x0010  # this is a ten bit chip address
I2C_M_RD              = 0x0001  # read data, from slave to master
I2C_M_STOP            = 0x8000  # if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_NOSTART         = 0x4000  # if I2C_FUNC_NOSTART
I2C_M_REV_DIR_ADDR    = 0x2000  # if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_IGNORE_NAK      = 0x1000  # if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_NO_RD_ACK       = 0x0800  # if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_RECV_LEN        = 0x0400  # length will be first received byte

I2C_SLAVE             = 0x0703  # Use this slave address
I2C_SLAVE_FORCE       = 0x0706  # Use this slave address, even if
                                # is already in use by a driver!
I2C_TENBIT            = 0x0704  # 0 for 7 bit addrs, != 0 for 10 bit
I2C_FUNCS             = 0x0705  # Get the adapter functionality mask
I2C_RDWR              = 0x0707  # Combined R/W transfer (one STOP only)
I2C_PEC               = 0x0708  # != 0 to use PEC with SMBus
I2C_SMBUS             = 0x0720  # SMBus transfer


CMD_START_FLOW = struct.pack(">H", 0x1000)
CMD_START_TEMP = struct.pack(">H", 0x1000)
CMD_RESET = struct.pack(">H", 0x2000)
CMD_RD_SCALE = struct.pack(">H", 0x30de)
CMD_RD_OFFSET = struct.pack(">H", 0x30df)
CMD_RD_SERNUM_1 = struct.pack(">H", 0x31ae)
CMD_RD_SERNUM_2 = struct.pack(">H", 0x31af)
CMD_RD_ARTICLE_1 = struct.pack(">H", 0x31e3)
CMD_RD_ARTICLE_2 = struct.pack(">H", 0x31e4)

VOL_L_MIN = -1.0
VOL_L_MAX = 5.0

FLOW_SLM_MIN = -75.0
FLOW_SLM_MAX = 75.0

class SFM3x00(object):
    def __init__(self, bus=1, address=0x40):
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

    def pos_raw(self, vmin, vmax, width, val, refval=0.0, mark="#"):
        clamped = max(min(val, vmax), vmin)
        scaled = int((clamped - vmin) * (width / (vmax - vmin)))
        scaled0 = int((refval - vmin) * (width / (vmax - vmin))) 
        pstr = [" "] * width
        pstr[scaled0] = "|"
        pstr[scaled] = "#"
        return "".join(pstr)

    def pos_slm(self, val, width=40):
        return self.pos_raw(FLOW_SLM_MIN, FLOW_SLM_MAX, width, val)

    def pos_l(self, val, width=40):
        return self.pos_raw(VOL_L_MIN, VOL_L_MAX, width, val)

    def _select_device(self, addr):
        """Set the address of the device to communicate with on the I2C bus."""
        ioctl(self._device.fileno(), I2C_SLAVE, addr & 0x7F)
        
    def write_bytes(self, bytes):
        assert self._device is not None, 'Bus must be opened before operations are made against it!'
        self._select_device(self.address)
        return self._device.write(bytes)

    def read_bytes(self, number):
        """Read many bytes from the specified device."""
        assert self._device is not None, 'Bus must be opened before operations are made against it!'
        self._select_device(self.address)
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
                         

        
if __name__ == "__main__":
    dwell = 0.020
    n_readings = 0
    with SFM3x00() as s:
        print("Serial Number: {}".format(s.read_serial_number()))
        offset = s.read_offset()
        print("Value offset: {}".format(offset))
        scale = s.read_scale()
        print("Value scale: {}".format(scale))
        print("Starting flow measurements")
        s.start_sensor()
        time.sleep(0.100)
        total_volume = 0.0
        last_t = time.time()
        last_print = last_t
        t = last_t
        while True:
            deltaT = t - last_t
            value = s.read_value()
            slm = (value - offset) / float(scale) 
            sl = (deltaT / 60.0) * slm
            total_volume = total_volume + sl
            n_readings = n_readings + 1
            t_str = time.strftime("%H:%M:%S", time.localtime(t))
	    if n_readings % 10 == 0:
                print(u"{:>8} dT {:>6.1f}ms | {:>10.2f} slm | {} | {} | {:>10.1f} cc".format(t_str, deltaT*1000, slm, s.pos_slm(slm), s.pos_l(total_volume), total_volume*1000))
            last_t = t
            time.sleep(dwell)
            t = time.time()
            
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
