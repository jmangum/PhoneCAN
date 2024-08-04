# PhoneCAN: A CAN Bus Home Sensor Network

Jeff Mangum

Have you ever wondered what you can do with your unused twisted-pair telephone wire running throughout your house?  Well, how about using it as the transport medium for a CAN bus network of environmental sensors?  This is a relatively easy project which uses Adafruit hardware and CiruitPython.

# Hardware
* Home Node (Node 0):
   - [Adafruit RP2040 CAN Feather with MCP2515 CAN Controller](https://www.adafruit.com/product/5724)
   - [Adafruit Featherwing 128x64 OLED](https://www.adafruit.com/product/4650)
* Remote Nodes (Nodes 1 through 3):
   - Nodes 1 and 2: [Adafruit RP2040 CAN Feather with MCP2515 CAN Controller](https://www.adafruit.com/product/5724)
   - Node 3 (Send Node): [Adafruit ESP32-S3 Feather with 4MB Flash 2MB PSRAM](https://www.adafruit.com/product/5477) with [Adafruit CAN Bus Featherwing MCP2515](https://www.adafruit.com/product/5709)
* Sensors:
   - 3 – [Adafruit Sensirion SHT41 Temperature and Humidity Sensor](https://www.adafruit.com/product/5776)
   - 1 – [Adafruit MS8607 Pressure Humidity Temperature PHT Sensor](https://www.adafruit.com/product/4716)
* CAN network wiring: Home telephone wiring (4 strand with 2 twisted pair; I believe that the standard is RJ-11)
* All nodes connected to power using AC-to-UBS converters, and all nodes equipped with LiPo batteries.  Test of remote node with [Adafruit 3.7v 2500Ah LiPo battery](https://www.adafruit.com/product/328) indicated that remote node can send measurements every second for about 1.5 days on battery power.

This configuration results in needing to have two “listen” nodes: one for the real-time display (Home Node) and a second for sending measurements to Adafruit IO (Send Node).  This seemed to work fine for my application.  One could possibly reduce this to one listen node (by stacking the OLED on the ESP32-S3 Feather).  On the other hand, separating the send functionality from the real-time display meant that I could put the send node at one of the remote locations (which could be chosen to be more accessible to wifi).

No special wiring or pin assignments needed (all plug-and-play).  Word of warning, though, when using RJ-11 patch cables.  Some cables are “swapped” (black-red-green-yellow on one end, yellow-green-red-black on the other end), while others are “straight”.  Since most of the connectors are see-through plastic, you can simply look at the colors of the wires in the connectors to see if you are using a swapped or straight patch cable.  I used all three wires (H, L, and ground) for the CAN bus connections.  See connection assignments used in Table 1.  Did not notice any problems (i.e. dropped packets) with this four CAN node setup.

The Home Node (node 0), with is the one with the OLED display, allows one to display real-time measurements from all nodes using the three buttons on the OLED Featherwing.  The OLED button reader library I used allowed for complex short-, long-, or multi-click input to select each of the four nodes to display.  I found that in order to display the fourth node (node 3 in my setup) that I had to use a long-click as I could not get the multi-click capability to work.

| Wire Color	| RJ11 Pin Number	| CAN Bus Wire Assignment |
| --- | --- | --- |
| Straight RJ11 CAN Bus Node Wiring | | |
| Red	| 3	| H |
| Black	| 2	| Ground |
| Green	| 4	| L |
| Crossed RJ11 CAN Bus Node Wiring | | |
| Red	| 4	| H |
| Black	| 5	| Ground |
| Green	| 3	| L |

# Software
* CircuitPython 9.1.1
* All libraries from CircuitPython 9.x standard and community bundle (OLED button reader library was from community bundle)
* Used cooperative multitasking (asyncio) to manage sensor read, CAN bus send, OLED display, and Adafruit IO upload tasks.
* Sample `code.py` for each node:
  - [`code_humenode.py`](code_homenode.py): Home (node 0) with OLED display.  Allows one to check values for all nodes using OLED push-buttons.
  - [`code_sendnode.py`](code_sendnode.py): Send (node 3) remote node which handles sending measurements to Adafruit IO on specified interval.
  - [`code_remote1.py`](code_remote1.py]: Sample remote (node 1) node.
  - [`code_remote2.py`](code_remote2.py]: Sample remote (node 2) node.
* Operational Comments:
  - OLED display button press response: Normally responds with updated values from requested node within a second, but sometimes might take two or three.
  - Upload interval to Adafruit IO is a setable parameter (I used 15 minutes).
  - I have not tested my CAN bus speed, but noted no dropped packets during my testing.  Note that my environment is a three-story house, so the twisted pair cable runs are quite long (hundreds of feet).
  - My system comprised of four nodes is by no means a limit to the number of nodes one can have.
  - I had to use the CircuitPython garbage collector in my send node as the averaging process over the specified upload to Adafruit IO interval sometimes uses a lot of memory.  I used a list comprehension, which I thought was pretty efficient, but perhaps there are more efficient means.

See my [description document](<docs/CAN Bus Home Sensor Network.docx>) for photos of my four-node setup.

