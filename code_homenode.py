#
# CAN bus environmental monitoring network home node
#
# Adafruit RP2040 CAN Feather
# Sensor: SHT41 temp and humidity sensor (can also use BME680 or MS8607 and read only use temp and relative humidity)
# Button A: Display home node sensor values
# Button B: Display remote 0 node sensor values
#
# Each remote node ID is given a number (0, 1, 2, etc.)
# Measurements are given ID as follows:
#   ID = even (0, 2, 4, etc. for nodeid 0, 1, 2, etc.) = temperature
#   ID = odd (1, 3, 5, etc. for nodeid 0, 1, 2, etc.) = humidity
#
# Jeff Mangum 2024-06-23

from time import sleep
import struct
import board
import busio
from digitalio import DigitalInOut, Direction, Pull
import displayio
from adafruit_mcp2515.canio import Message, RemoteTransmissionRequest, Match
from adafruit_mcp2515 import MCP2515 as CAN
#from adafruit_ms8607 import MS8607
#import adafruit_bme680
import adafruit_sht4x
import asyncio
from async_button import Button, MultiButton
import neopixel

# This is nodeid 0, so offset is 0
nodeid = 0
offset = 0

# nodeid to measurement ID correspondence
meastonodeid = [0,0,1,1,2,2,3,3,4,4,5,5]

read_interval = 0 # Seconds.  For CAN bus read.  Set to 0 to allow continuous CAN bus clearing.
send_interval = 1 # Seconds.  Send should be much shorter than read to assure values are available on bus.
can_listen_timeout = 5.0 # Interval during which CAN bus messages are read from the bus.  Set to several seconds
                         #   to allow time for all nodes to report.

# Neopixel settings
brightval = 0.01 # Use dim setting for bedrooms...
color = 0x6600CC # Dark purple

# Setup neopixel
np = neopixel.NeoPixel(board.NEOPIXEL,1,brightness=brightval)

class Context():
    # Pass variables around to any routine that needs them
    def __init__(self,selected_button,click_name,can_bus,sensor,label,terminalio,xpos,ypos,text_area,splash,read_interval,send_interval,can_listen_timeout,nodeid,offset):
        self.selected_button = selected_button
        self.click_name = click_name
        self.can_bus = can_bus
        self.sensor = sensor
        self.label = label
        self.terminalio = terminalio
        self.xpos = xpos
        self.ypos = ypos
        self.text_area = text_area
        self.splash = splash
        self.read_interval = read_interval
        self.send_interval = send_interval
        self.can_listen_timeout = can_listen_timeout
        self.nodeid = nodeid
        self.offset = offset


def canstate(can_bus):
    # Check CAN bus state
    if can_bus.state != 0:
        print("BUS STATE: ",can_bus.state)
        can_bus.restart()


async def button_func(context: Context):
    nodetobutton = ["a","b","c","c"]
    nodetoclick = ["Single click","Single click","Single click","Long click"]
    while True:
        if context.selected_button == nodetobutton[0] and context.click_name == nodetoclick[0]:
            #print(context.selected_button,context.click_name)
            home_temp = context.sensor.temperature
            home_rh = context.sensor.relative_humidity
            #print("Local Temp: ",home_temp)
            #print("Local RH: ",home_rh)
            context.text_area[0] = context.label.Label(context.terminalio.FONT, text="Home", color=0xFFFFFF, x=context.xpos[0], y=context.ypos[0])
            if len(context.splash) > 5:
                context.splash.pop(5)
            context.splash.insert(5,context.text_area[0])
            context.text_area[1] = context.label.Label(context.terminalio.FONT, text="{:.2f}".format(home_temp), color=0xFFFFFF, x=context.xpos[1], y=context.ypos[1])
            if len(context.splash) > 6:
                context.splash.pop(6)
            context.splash.insert(6,context.text_area[1])
            context.text_area[2] = context.label.Label(context.terminalio.FONT, text="{:.2f}".format(home_rh), color=0xFFFFFF, x=context.xpos[2], y=context.ypos[2])
            if len(context.splash) > 7:
                context.splash.pop(7)
            context.splash.insert(7,context.text_area[2])
            sleep(1)
        else:
            canstate(context.can_bus)
            # Listen for context.can_listen_timeout seconds to allow all nodes to report...
            with context.can_bus.listen(timeout=context.can_listen_timeout) as listener:
                message_count = listener.in_waiting()
                for _i in range(message_count):
                    #print(message_count, "messages available")
                    #print("Receive Error Count: ",context.can_bus.receive_error_count)
                    msg = listener.receive()
                    #print("Message from ", hex(msg.id))
                    #if isinstance(msg, Message):
                        #print("Message Data: ",struct.unpack('<HH',msg.data))
                    #if isinstance(msg, RemoteTransmissionRequest):
                        #print("RTR length:", msg.length)
                    rxnodeid = meastonodeid[msg.id]
                    #print("Received message from node: ",nodeid)
                    print("Message from node: ", rxnodeid, "Message Data: ",struct.unpack('<HH',msg.data))
                    #
                    # Display node based on selected button and number of button presses...
                    if context.selected_button == nodetobutton[rxnodeid] and context.click_name == nodetoclick[rxnodeid]:
                        msg_unpack = int(struct.unpack('<HH',msg.data)[0])+float(struct.unpack('<HH',msg.data)[1]/1000)
                        # Message ID to value correspondence: (0,1,2) = (P,T,RH)
                        #for i in range(3):
                        #if msg.id == 0:
                        #    text_area[0] = label.Label(terminalio.FONT, text=str(msg_unpack), color=0xFFFFFF, x=xpos[0], y=ypos[0])
                        #    if len(splash) > 5:
                        #        splash.pop(5)
                        #    splash.insert(5, text_area[0])
                        context.text_area[0] = context.label.Label(context.terminalio.FONT, text="Remote "+str(rxnodeid), color=0xFFFFFF, x=context.xpos[0], y=context.ypos[0])
                        if len(context.splash) > 5:
                            context.splash.pop(5)
                        context.splash.insert(5,context.text_area[0])
                        if msg.id % 2 == 0: # Check to see if msg.id is even
                            context.text_area[1] = context.label.Label(context.terminalio.FONT, text="{:.2f}".format(msg_unpack), color=0xFFFFFF, x=context.xpos[1], y=context.ypos[1])
                            if len(context.splash) > 6:
                                context.splash.pop(6)
                            context.splash.insert(6,context.text_area[1])
                        else: # If msg.id is not even, it must be odd...
                            context.text_area[2] = context.label.Label(context.terminalio.FONT, text="{:.2f}".format(msg_unpack), color=0xFFFFFF, x=context.xpos[2], y=context.ypos[2])
                            if len(context.splash) > 7:
                                context.splash.pop(7)
                            context.splash.insert(7,context.text_area[2])
        await asyncio.sleep(context.read_interval)


# Listen for button presses
async def button_listener(context: Context, multibutton):
    print("\nIn button_listener...")
    CLICK_NAMES = {
        Button.SINGLE: "Single click",
        Button.DOUBLE: "Double click",
        Button.TRIPLE: "Triple click",
        Button.LONG: "Long click",
        }
    context.selected_button = "a" #None
    context.click_name = "Single click"
    while True:
        old_selected_button = context.selected_button
        old_click_name = context.click_name
        button_name, click = await multibutton.wait(a=Button.ANY_CLICK, b=Button.ANY_CLICK, c=Button.ANY_CLICK)
        print("button_name in button_listener: ",button_name)
        print("click in button_listener: ",CLICK_NAMES[click])
        context.selected_button = button_name
        context.click_name = CLICK_NAMES[click]
        # When a click is received, set context.read_interval to 0 to get immediate read and display of sensor values
        if (context.selected_button != old_selected_button) and (context.click_name != old_click_name):
            context.send_interval = 0
        else:
            context.send_interval = send_interval
        await asyncio.sleep(0)


async def sendmeas(context: Context):
    # Send out this node's (nodeid = 3) measurements onto the CAN bus...
    while True:
        measlist = []
        #print("Pressure: %.2f hPa" % sensor.pressure)
        #print("Temperature: %.2f C" % sensor.temperature)
        #print("Humidity: %.2f %% rH" % sensor.relative_humidity)
        #print("\n------------------------------------------------\n")
        #ip, sp = divmod(sensor.pressure, 1)
        #ps = struct.pack('<HH', int(ip), int(1000*sp))
        #measlist.append(ps)
        it, st = divmod(context.sensor.temperature, 1)
        ts = struct.pack('<HH', int(it), int(1000*st))
        measlist.append(ts)
        ih, sh = divmod(context.sensor.relative_humidity, 1)
        rs = struct.pack('<HH', int(ih), int(1000*sh))
        measlist.append(rs)
        for meas in measlist:
            #print("len(measlist): ",len(measlist)," and meas: ",meas)
            np.fill(color)
            context.message = Message(id=measlist.index(meas)+context.offset, data=meas, extended=True)
            send_success = context.can_bus.send(context.message)
            #print("Send measurement ",measlist.index(meas)," success:", send_success)
            np.fill(0)
        #print("Transmit Error Count: ",can_bus.transmit_error_count)
        await asyncio.sleep(context.send_interval)

async def main():
    # Define buttons A, B, and C
    # note Button must be created in an async environment
    button_a = Button(
        board.D9,
        value_when_pressed=False,
        double_click_enable=True,
        triple_click_enable=True,
        long_click_enable=True,
    )
    button_b = Button(
        board.D6,
        value_when_pressed=False,
        double_click_enable=True,
        triple_click_enable=True,
        long_click_enable=True,
    )
    button_c = Button(
        board.D5,
        value_when_pressed=False,
        double_click_enable=True,
        triple_click_enable=True,
        long_click_enable=True,
    )
    multibutton = MultiButton(a=button_a, b=button_b, c=button_c)

    # Compatibility with both CircuitPython 8.x.x and 9.x.x.
    # Remove after 8.x.x is no longer a supported release.
    try:
        from i2cdisplaybus import I2CDisplayBus
    except ImportError:
        from displayio import I2CDisplay as I2CDisplayBus

    import terminalio

    # Setup CAN bus
    cs = DigitalInOut(board.CAN_CS)
    cs.switch_to_output()
    spi = board.SPI()

    can_bus = CAN(
        spi, cs, loopback=False, silent=False
    )  # use loopback and silent True to test without another device

    # can try import bitmap_label below for alternative
    from adafruit_display_text import label
    import adafruit_displayio_sh1107

    displayio.release_displays()
    # oled_reset = board.D9

    # Use for I2C
    i2c = board.I2C()  # uses board.SCL and board.SDA
    display_bus = I2CDisplayBus(i2c, device_address=0x3C)
    #sensor = MS8607(i2c)

    # Initialize local environmental conditions sensor
    #sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)
    sensor = adafruit_sht4x.SHT4x(i2c)

    # SH1107 is vertically oriented 64x128
    WIDTH = 128
    HEIGHT = 64
    BORDER = 2
    NMEAS = 2 # Number of measurements to display (temperature and relative humidity for this implementation)

    # Initialize size of splash and display variables
    splash_init = 5
    xposstatic = [8,8,8]
    yposstatic = [10,30,50]
    xpos = [75,75,75]
    ypos = [10,30,50]
    text_area = [None]*3
    selected_button = None
    click_name = None

    display = adafruit_displayio_sh1107.SH1107(
        display_bus, width=WIDTH, height=HEIGHT, rotation=0
    )

    # Make the display context
    splash = displayio.Group()
    display.root_group = splash

    color_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
    color_palette = displayio.Palette(1)
    color_palette[0] = 0xFFFFFF  # White

    bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
    splash.append(bg_sprite)

    # Draw a smaller inner rectangle in black
    inner_bitmap = displayio.Bitmap(WIDTH - BORDER * 2, HEIGHT - BORDER * 2, 1)
    inner_palette = displayio.Palette(1)
    inner_palette[0] = 0x000000  # Black
    inner_sprite = displayio.TileGrid(
        inner_bitmap, pixel_shader=inner_palette, x=BORDER, y=BORDER
    )
    splash.append(inner_sprite)

    # Setup static part of display
    text_static_title = label.Label(terminalio.FONT, text='Sensor Loc: ', color=0xFFFFFF, x=xposstatic[0], y=yposstatic[0])
    splash.append(text_static_title)
    #text_static_pres_area = label.Label(terminalio.FONT, text='Pres (hPa): ', color=0xFFFFFF, x=8, y=10)
    #splash.append(text_static_pres_area)
    text_static_temp_area = label.Label(terminalio.FONT, text='Temp (C): ', color=0xFFFFFF, x=xposstatic[1], y=yposstatic[1])
    splash.append(text_static_temp_area)
    text_static_rh_area = label.Label(terminalio.FONT, text='RH (%): ', color=0xFFFFFF, x=xposstatic[2], y=yposstatic[2])
    splash.append(text_static_rh_area)
    my_context = Context(selected_button, click_name, can_bus, sensor, label, terminalio, xpos, ypos, text_area, splash, read_interval, send_interval, can_listen_timeout, nodeid, offset)
    button_func_task = asyncio.create_task(button_func(my_context))
    button_listener_task = asyncio.create_task(button_listener(my_context, multibutton))
    sendmeas_task = asyncio.create_task(sendmeas(my_context))
    await asyncio.gather(button_func_task, button_listener_task, sendmeas_task)

asyncio.run(main())