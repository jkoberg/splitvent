
from fcntl import ioctl
import math, struct, time, collections, argparse, multiprocessing
from collections import namedtuple


"""Pure-python interface for Honeywell TruStability SSC-series pressure sensors"""

I2C_SLAVE                        = 0x0703  #  Linux Kernel Constant for ioctl on /dev/i2c-*

RASPI_DEFAULT_I2C_BUS            = 1

HONEYWELL_SSC_DEFAULT_I2C_ADDR_2 = 0x28
HONEYWELL_SSC_DEFAULT_I2C_ADDR_3 = 0x38
HONEYWELL_SSC_DEFAULT_I2C_ADDR_4 = 0x48
HONEYWELL_SSC_DEFAULT_I2C_ADDR_5 = 0x58
HONEYWELL_SSC_DEFAULT_I2C_ADDR_6 = 0x68
HONEYWELL_SSC_DEFAULT_I2C_ADDR_7 = 0x78


HoneywellSSCRange = namedtuple("HoneywellSSCRange", ["min", "max", "unit", "convFactor"])
HoneywellSSCTransferFunction = namedtuple("HoneywellSSCTransferFunction", ["report_min", "report_max"])

cmH2O_per_psi = 70.307

HONEYWELL_SSC_RANGES = {
    '005PG': HoneywellSSCRange(0.0,  5.0, "psig", cmH2O_per_psi),
    '015PG': HoneywellSSCRange(0.0, 15.0, "psig", cmH2O_per_psi),
}

HONEYWELL_TRANSFER_FUNCS = {
    "A": HoneywellSSCTransferFunction(0.10 * 2**14,  0.90 * 2**14),
    "B": HoneywellSSCTransferFunction(0.05 * 2**14,  0.95 * 2**14),
    "C": HoneywellSSCTransferFunction(0.05 * 2**14,  0.85 * 2**14),
    "F": HoneywellSSCTransferFunction(0.04 * 2**14,  0.94 * 2**14)
}
HONEYWELL_SSC_TRANSFERFUNC_A = HoneywellSSCTransferFunction(2**14 * 0.10, 2**14 * 0.90)

cmH2OReading = namedtuple("cmH2OReading", ["cmH2O"])


class HoneywellSSC(object):
    """Read Honeywell SSC sensor readings over I2C"""

    def __init__(self, range=HONEYWELL_SSC_RANGES['015PG'], transferfunc=HONEYWELL_TRANSFER_FUNCS['A'], address=HONEYWELL_SSC_DEFAULT_I2C_ADDR_2, bus=RASPI_DEFAULT_I2C_BUS):
        self.range = range
        self.transferfunc = transferfunc
        self.scale_factor = (self.range.max - self.range.min) / (self.transferfunc.report_max - self.transferfunc.report_min)
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

    def read_value(self):
        bytes = self.read_bytes(2)
        (report,) = struct.unpack(">H", bytes)
        if report & 0xc000:
            raise Exception("Honeywell sensor diagnostic condition reported. Sensor may have failed.")
        pressure_raw = report & 0x3fff
        return pressure_raw

    def scale_value(self, reported):
        return ((self.scale_factor * (reported - self.transferfunc.report_min)) + self.range.min) * self.range.convFactor

    def prepare(self):
        pass

    def read_scaled(self):
        return self.scale_value(self.read_value())


