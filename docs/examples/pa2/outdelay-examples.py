#!/usr/bin/env python3

"""
Connects to a single DriveRack PA2 on the network.
Prints the current High band output delay settings.
Creates 3 output delays sets them if the current configuration supports them.
Waits a couple seconds, refreshes state, and decreases the delay on the high band by -3.5ms.
"""

import time

import dbxdriverack.pa2 as pa2
import dbxdriverack.pa2.outputdelay as odly
import dbxdriverack.pa2.outputband as ob

timeout = 3


# Create 3 output delays

delayHigh = odly.PA2OutputDelay()
delayHigh.setDelay(5.3)
delayHigh.enable()

delayMid = odly.PA2OutputDelay()
delayMid.setDelay(6.0)
delayMid.disable()

delayLow = odly.PA2OutputDelay()
delayLow.setDelay(1.7)
delayLow.enable()

# Connect and apply

with pa2.PA2(debug=False) as drack:
    devices = drack.discoverDevices(timeout=timeout)
    if len(devices) != 1:
        raise Exception("Did not find exactly 1 DriveRack PA2 online")
    address = next(iter(devices))[0]
    drack.connect(address)

    currentHigh = drack.getOutputDelay(ob.BandHigh)
    print(currentHigh)

    drack.setOutputDelay(ob.BandHigh, delayHigh)

    if drack.hasMids():
        print("Mid band exists: Setting output delay")
        drack.setOutputDelay(ob.BandMid, delayMid)

    if drack.hasSubs():
        print("Sub band exists: Setting output delay")
        drack.setOutputDelay(ob.BandLow, delayLow)

    time.sleep(2)

    # Refresh state
    delayHigh = drack.getOutputDelay(ob.BandHigh)
    delayHigh.setDelay(delayHigh.getDelay() - 3.5)
    drack.setOutputDelay(ob.BandHigh, delayHigh)
