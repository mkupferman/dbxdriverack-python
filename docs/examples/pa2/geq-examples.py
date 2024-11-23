#!/usr/bin/env python3

"""
Connects to a single DriveRack PA2 on the network.
Prints the current GEQ enabled state (left or stereo-linked).
Get the current (left or stereo-linked) GEQ, the first and last 3 bands,
modifying the middle bands only.

If it's set in dual-mono GEQ mode, set the 2nd GEQ to the right channel GEQ.
"""

import math

import dbxdriverack as dr
import dbxdriverack.pa2 as pa2
import dbxdriverack.pa2.geq as geq

timeout = 3


# Create a GEQs for later use

graphicEq2 = geq.PA2Geq()
for bandNumber in range(10, 26):
    value = 12 * math.sin(2 * math.pi * (bandNumber - 10) / 16)
    graphicEq2.setBand(bandNumber, value)
graphicEq2.disable()

# Connect and apply

with pa2.PA2(debug=False) as drack:
    devices = drack.discoverDevices(timeout=timeout)
    if len(devices) != 1:
        raise Exception("Did not find exactly 1 DriveRack PA2 online")
    address = next(iter(devices))[0]
    drack.connect(address)

    # Get the current GEQ
    if drack.isGeqStereo():
        # single GEQ to control
        graphicEq1 = drack.getGeq()
    else:
        # 2 EQs to control
        graphicEq1 = drack.getGeq(channel=dr.ChannelLeft)
        # Set the 2nd GEQ now
        drack.setGeq(graphicEq2, channel=dr.ChannelRight)

    print(graphicEq1)

    # Modify the middle bands of GEQ1
    for bandNumber in range(4, 29):
        value = 12 * math.cos(2 * math.pi * (bandNumber - 4) / 25)
        graphicEq1.setBand(bandNumber, value)

    # Apply EQ1's changes
    if drack.isGeqStereo():
        drack.setGeq(graphicEq1)
    else:
        drack.setGeq(graphicEq1, channel=dr.ChannelLeft)
