#
# CAN bus network remote node
# Adafruit RP2040 CAN with SHT41 temperature and humidity sensor
# Each remote node ID is given a number (0, 1, 2, etc.)
# Measurements are given ID as follows:
#   ID = even (0, 2, 4, etc. for nodeid 0, 1, 2, etc.) = temperature
#   ID = odd (1, 3, 5, etc. for nodeid 0, 1, 2, etc.) = humidity
#
# Jeff Mangum 2024-06-29
#
from time import sleep
import struct
import board
import binascii
from digitalio import DigitalInOut
from adafruit_mcp2515.canio import Message, RemoteTransmissionRequest
from adafruit_mcp2515 import MCP2515 as CAN
#from adafruit_ms8607 import MS8607
import adafruit_sht4x
import neopixel

# This is node 2, so offset is 4
nodeid = 2
offset = 4

# Set measurement loop sleep time, which sets measurement send interval
sendint = 1.0 # Seconds

# Neopixel settings
brightval = 0.01 # Use dim setting for bedrooms...
color = 0x6600CC # Dark purple

# Setup neopixel
np = neopixel.NeoPixel(board.NEOPIXEL,1,brightness=brightval)

# Setup CAN bus
cs = DigitalInOut(board.CAN_CS)
cs.switch_to_output()
spi = board.SPI()

can_bus = CAN(
    spi, cs, loopback=False, silent=False
)  # use loopback and silent True to test without another device

# Use for I2C
i2c = board.I2C()  # uses board.SCL and board.SDA
#sensor = MS8607(i2c)
sensor = adafruit_sht4x.SHT4x(board.I2C())

while True:
    print("BUS STATE: ",can_bus.state)
    if can_bus.state != 0:
        can_bus.restart()
    measlist = []
    #print("Pressure: %.2f hPa" % sensor.pressure)
    print("Temperature: %.2f C" % sensor.temperature)
    print("Humidity: %.2f %% rH" % sensor.relative_humidity)
    print("\n------------------------------------------------\n")
    #ip, sp = divmod(sensor.pressure, 1)
    #ps = struct.pack('<HH', int(ip), int(1000*sp))
    #measlist.append(ps)
    it, st = divmod(sensor.temperature, 1)
    ts = struct.pack('<HH', int(it), int(1000*st))
    measlist.append(ts)
    ih, sh = divmod(sensor.relative_humidity, 1)
    rs = struct.pack('<HH', int(ih), int(1000*sh))
    measlist.append(rs)
    print("This is node :",nodeid)
    for meas in measlist:
        np.fill(color)
        message = Message(id=measlist.index(meas)+offset, data=meas, extended=True)
        send_success = can_bus.send(message)
        print("Send measurement ",measlist.index(meas)," success:", send_success)
        np.fill(0)
    print("Transmit Error Count: ",can_bus.transmit_error_count)
    sleep(sendint)