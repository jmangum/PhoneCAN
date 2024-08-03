#
# CAN bus network remote node
# Adafruit ESP32-S3 with CAN Featherwing and SHT41 temperature and humidity sensor
# Each remote node ID is given a number (0, 1, 2, etc.)
# Measurements are given ID as follows:
#   ID = even (0, 2, 4, etc. for nodeid 0, 1, 2, etc.) = temperature
#   ID = odd (1, 3, 5, etc. for nodeid 0, 1, 2, etc.) = humidity
#
# This node will handle pushing measurements up to AIO
#
# Jeff Mangum 2024-07-01
#
import struct
import ulab.numpy
import board
import busio
import binascii
from digitalio import DigitalInOut
from adafruit_mcp2515.canio import Message, RemoteTransmissionRequest, Match
from adafruit_mcp2515 import MCP2515 as CAN
#from adafruit_ms8607 import MS8607
import adafruit_sht4x
import time
import ssl
import os
from random import randint
import microcontroller
import socketpool
import wifi
import neopixel
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
import asyncio
import gc

gc.enable() # Enable garbage collection

# This is node 3, so offset is 6
nodeid = 3
offset = 6

print("This is node :",nodeid)

send_interval = 1 # Seconds
read_interval = 0.5 # Seconds.  Read should be shorter than send to assure values on the bus.
publish_interval = 60*15 # Seconds
can_listen_timeout = 5.0 # Seconds.  Interval during which CAN bus messages are read from the bus.  Set to several seconds
                         #   to allow time for all nodes to report.

# nodeid to measurement ID correspondence
meastonodeid = [0,0,1,1,2,2,3,3,4,4,5,5]

# Neopixel settings
brightval = 0.3 # Use dim setting for bedrooms...
color = 0x6600CC # Dark purple

# Setup neopixel
np = neopixel.NeoPixel(board.NEOPIXEL,1,brightness=brightval)

# Setup CAN bus on featherwing
cs = DigitalInOut(board.D5)
cs.switch_to_output()
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)

can_bus = CAN(
    spi, cs, loopback=False, silent=False
)  # use loopback and silent True to test without another device
print("BUS STATE: ",can_bus.state)

# Use for I2C
i2c = board.I2C()  # uses board.SCL and board.SDA
#sensor = MS8607(i2c)
sensor = adafruit_sht4x.SHT4x(board.I2C())

# WiFi
try:
    print("Connecting to %s" % os.getenv("CIRCUITPY_WIFI_SSID"))
    wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
    print("Connected to %s!" % os.getenv("CIRCUITPY_WIFI_SSID"))
# Wi-Fi connectivity fails with error messages, not specific errors, so this except is broad.
except Exception as e:  # pylint: disable=broad-except
    print("Failed to connect to WiFi. Error:", e, "\nBoard will hard reset in 30 seconds.")
    time.sleep(30)
    microcontroller.reset()


# Define callback functions which will be called when certain events happen.
def connected(client):
    print("Connected to MQTT Broker!")
    # Subscribe to Adafruit IO group called "CANnetwork"
    group_name = "cannetwork"
    client.subscribe(group_key=group_name)
    #client.subscribe_to_errors()
    #node_feed = "cannetwork.nodeid"
    #temp_feed = "cannetwork.nodetemp"
    #humid_feed = "cannetwork.nodehumid"


def disconnected(client):
    # This method is called when the client disconnects
    # from the broker.
    print("Disconnected from MQTT Broker!\n")


def message(client, feed_id, payload):  # pylint: disable=unused-argument
    print("Feed {0} received new value: {1}".format(feed_id, payload))


def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))


def unsubscribe(client, userdata, topic, pid):
    # This method is called when the client unsubscribes from a feed.
    print("Unsubscribed from {0} with PID {1}".format(topic, pid))


def publish(client, userdata, topic, pid):
    # This method is called when the client publishes data to a feed.
    print("Published to {0} with PID {1}".format(topic, pid))


# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=os.getenv("ADAFRUIT_AIO_USERNAME"),
    password=os.getenv("ADAFRUIT_AIO_KEY"),
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Initialize Adafruit IO MQTT "helper"
io = IO_MQTT(mqtt_client)

# Set up the callback methods above
io.on_connect = connected
io.on_disconnect = disconnected
io.on_message = message
io.on_subscribe = subscribe
io.on_publish = publish


# If Adafruit IO is not connected...
if not io.is_connected:
    # Connect the client to the MQTT broker.
    print("Connecting to MQTT Broker...")
    io.connect()


class Common():
    # Pass variables around
    def __init__(self, connected, message, io, sensor, can_bus, nodeid, offset, rxnode, temp, humid, read_interval, send_interval, publish_interval, can_listen_timeout, node_feed, temp_feed, humid_feed):
        self.connected = connected
        self.message = message
        self.io = io
        self.sensor = sensor
        self.can_bus = can_bus
        self.nodeid = nodeid
        self.offset = offset
        self.rxnode = rxnode
        self.temp = temp
        self.humid = humid
        self.read_interval = read_interval
        self.send_interval = send_interval
        self.publish_interval = publish_interval
        self.can_listen_timeout = can_listen_timeout
        self.node_feed = node_feed
        self.temp_feed = temp_feed
        self.humid_feed = humid_feed


async def sendmeas(common: Common):
    # Send out this node's (nodeid = 3) measurements
    while True:
        measlist = []
        #print("Pressure: %.2f hPa" % sensor.pressure)
        #print("Temperature: %.2f C" % sensor.temperature)
        #print("Humidity: %.2f %% rH" % sensor.relative_humidity)
        #print("\n------------------------------------------------\n")
        #ip, sp = divmod(sensor.pressure, 1)
        #ps = struct.pack('<HH', int(ip), int(1000*sp))
        #measlist.append(ps)
        it, st = divmod(common.sensor.temperature, 1)
        ts = struct.pack('<HH', int(it), int(1000*st))
        measlist.append(ts)
        ih, sh = divmod(common.sensor.relative_humidity, 1)
        rs = struct.pack('<HH', int(ih), int(1000*sh))
        measlist.append(rs)
        for meas in measlist:
            #print("len(measlist): ",len(measlist)," and meas: ",meas)
            np.fill(color)
            common.message = Message(id=measlist.index(meas)+common.offset, data=meas, extended=True)
            send_success = common.can_bus.send(common.message)
            #print("Send measurement ",measlist.index(meas)," success:", send_success)
            np.fill(0)
        #print("Transmit Error Count: ",can_bus.transmit_error_count)
        await asyncio.sleep(common.send_interval)


async def collectnodes(common: Common):
    # Read measurements from all nodes every read_inverval seconds
    # Since nodes will not always report a temp and humid value at each read,
    #    need to associate each temp or humid value with a node.
    while True:
        #print("len(common.temp): ",len(common.temp))
        #print("common.temp: ",common.temp)
        #print("len(common.humid): ",len(common.humid))
        #print("common.humid: ",common.humid)
        #common.rxnode = []
        #common.temp = []
        #common.humid = []
        with common.can_bus.listen(timeout=can_listen_timeout) as listener:
            message_count = listener.in_waiting()
            #print(message_count, "messages available")
            #print("Receive Error Count: ",common.can_bus.receive_error_count)
            for _i in range(message_count):
                msg = listener.receive()
                #print("Message from ", hex(msg.id))
                #if isinstance(msg, Message):
                    #print("Message Data: ",struct.unpack('<HH',msg.data))
                #if isinstance(msg, RemoteTransmissionRequest):
                    #print("RTR length:", msg.length)
                #print("msg.id",msg.id)
                #print("Message Data: ",struct.unpack('<HH',msg.data))
                rxnodeid = meastonodeid[msg.id]
                #common.rxnode.append(rxnodeid)
                #
                msg_unpack = int(struct.unpack('<HH',msg.data)[0])+float(struct.unpack('<HH',msg.data)[1]/1000)
                #print("Received message from node: ",rxnodeid," measurement number: ",msg.id," msg_unpack: ",msg_unpack)
                # Message ID to value correspondence: (0,1,2) = (P,T,RH)
                # Stuff all (node,T,RH) measurements into lists for pushing up to AIO...
                if msg.id % 2 == 0: # Check to see if msg.id is even (Temperature measurement)
                    common.temp.append([rxnodeid,msg_unpack])
                else: # If msg.id is not even, it must be odd (Relative Humidity measurement)
                    common.humid.append([rxnodeid,msg_unpack])
        common.temp.append([3,sensor.temperature])
        common.humid.append([3,sensor.relative_humidity])
        await asyncio.sleep(common.read_interval)


async def publishtoaio(common: Common):
    print("In publishtoaio...")
    while True:
        # Check to make sure that MQTT broker is still connected
        if not io.is_connected:
            # Connect the client to the MQTT broker.
            print("Connecting to Adafruit IO...")
            io.reconnect()
        # Current date/time will be tagged by AIO
        # Calculate average values per node to send to AIO
        ndlist = [0,1,2,3]
        tempave = []
        humidave = []
        tempave.append(ulab.numpy.mean([i[1] for i in common.temp if i[0] == 0 and i[1] >= 0.0]))
        tempave.append(ulab.numpy.mean([i[1] for i in common.temp if i[0] == 1 and i[1] >= 0.0]))
        tempave.append(ulab.numpy.mean([i[1] for i in common.temp if i[0] == 2 and i[1] >= 0.0]))
        tempave.append(ulab.numpy.mean([i[1] for i in common.temp if i[0] == 3 and i[1] >= 0.0]))
        humidave.append(ulab.numpy.mean([i[1] for i in common.humid if i[0] == 0 and i[1] >= 0.0]))
        humidave.append(ulab.numpy.mean([i[1] for i in common.humid if i[0] == 1 and i[1] >= 0.0]))
        humidave.append(ulab.numpy.mean([i[1] for i in common.humid if i[0] == 2 and i[1] >= 0.0]))
        humidave.append(ulab.numpy.mean([i[1] for i in common.humid if i[0] == 3 and i[1] >= 0.0]))
        if io.is_connected:
            for node,t,rh in zip(ndlist,tempave,humidave):
                if t != 0 and rh != 0:
                    print("Publishing value {0} to feed: {1}".format(node,common.node_feed))
                    #common.io.publish(common.node_feed, node)
                    print("Publishing value {0} to feed: {1}".format(t,common.temp_feed))
                    #common.io.publish(common.temp_feed, t)
                    print("Publishing value {0} to feed: {1}\n".format(rh,common.humid_feed))
                    #common.io.publish(common.humid_feed, rh)
                    common.io.publish_multiple([(common.node_feed, node),(common.temp_feed, t), (common.humid_feed, rh)], timeout=1, is_group=True)
                else:
                    print("Not publishing value {0} to feed: {1}".format(node,common.node_feed))
                    print("Not publishing value {0} to feed: {1}".format(t,common.temp_feed))
                    print("Not publishing value {0} to feed: {1}\n".format(rh,common.humid_feed))
            print("\n")
            tempave = []
            humidave = []
            common.rxnode = []
            common.temp = []
            common.humid = []
            io.disconnect()
            gc.collect()
            print("Free Memory After Push to AIO: ",gc.mem_free())
        else:
            print("MQTT Broker or Wifi Not Connected...Going Back to Sleep...\n")
        await asyncio.sleep(common.publish_interval)


async def main():
    rxnode = []
    temp = []
    humid = []
    #group_name = "cannetwork"
    node_feed = "cannetwork.nodeid"
    temp_feed = "cannetwork.nodetemp"
    humid_feed = "cannetwork.nodehumid"
    #io.subscribe(group_key=group_name)
    _common = Common(connected, message, io, sensor, can_bus, nodeid, offset, rxnode, temp, humid, read_interval, send_interval, publish_interval, can_listen_timeout, node_feed, temp_feed, humid_feed)
    sendmeas_task = asyncio.create_task(sendmeas(_common))
    collectnodes_task = asyncio.create_task(collectnodes(_common))
    publishtoaio_task = asyncio.create_task(publishtoaio(_common))
    await asyncio.gather(sendmeas_task, collectnodes_task, publishtoaio_task)

asyncio.run(main())