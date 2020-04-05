
from fcntl import ioctl
import struct, time, collections


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
            self._select_device(self.address)
            self.offset = float(self.read_offset())
            self.scale = float(self.read_scale())
            self.serial_number = self.read_serial_number()
            print('Opened {} for device communications'.format(devicename))
        except IOError:
            print('Unable to open port {} for device communications'.format(devicename))
            print('Use the --fake flag to simulate a device for testing')
            raise
        
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

    def prepare(self):
        self.start_sensor()
        time.sleep(0.100)
        self.read_value()

    def read_scaled(self):
        value = self.read_value()
        return self.scale_value(value)


        
