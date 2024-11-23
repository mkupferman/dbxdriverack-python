#!/usr/bin/env python3

"""
Connects to a single DriveRack PA2 on the network.
Prints the current High band PEQ settings.
Creates 3 PEQs and sets them if the current configuration supports them.
Waits a couple seconds and flattens the High band EQ.
Waits a couple more seconds and restores the previous High EQ.
Waits a couple seconds, refreshes state, and disables the High band EQ.
"""

import time

import dbxdriverack.pa2 as pa2
import dbxdriverack.pa2.peq as peq
import dbxdriverack.pa2.outputband as ob

timeout = 3


# Create 3 PEQs

peqHigh = peq.PA2Peq()
peqFilter1 = peq.PA2PeqFilter(peq.LowShelf, 1000, 3, 5)
peqFilter2 = peq.PA2PeqFilter(peq.Bell, 1200, -8, 2)
peqFilter3 = peq.PA2PeqFilter(peq.HighShelf, 15000, -3, 3)
peqHigh.addFilter(peqFilter1)
peqHigh.addFilter(peqFilter2)
peqHigh.addFilter(peqFilter3)
peqHigh.enable()

peqMid = peq.PA2Peq()
peqBand1 = peq.PA2PeqFilter(peq.Bell, 700, -6, 5)
peqMid.addFilter(peqBand1)
peqMid.disable()

peqLow = peq.PA2Peq()
peqBand1 = peq.PA2PeqFilter(peq.LowShelf, 100, 6, 5)
peqBand2 = peq.PA2PeqFilter(peq.Bell, 63, -3, 12)
peqLow.addFilter(peqBand1)
peqLow.addFilter(peqBand2)
peqLow.enable()

# Connect and apply

with pa2.PA2(debug=False) as drack:
    devices = drack.discoverDevices(timeout=timeout)
    if len(devices) != 1:
        raise Exception("Did not find exactly 1 DriveRack PA2 online")
    address = next(iter(devices))[0]
    drack.connect(address)

    currentHigh = drack.getPeq(ob.BandHigh)
    print(currentHigh)

    drack.setPeq(ob.BandHigh, peqHigh)

    if drack.hasMids():
        print("Mid band exists: Setting PEQ")
        drack.setPeq(ob.BandMid, peqMid)

    if drack.hasSubs():
        print("Sub band exists: Setting PEQ")
        drack.setPeq(ob.BandLow, peqLow)

    time.sleep(2)

    print("Flattening High band EQ")
    drack.flattenPeq(ob.BandHigh)

    time.sleep(2)

    print("Restoring High band EQ")
    drack.unflattenPeq(ob.BandHigh)

    time.sleep(2)

    peqHigh = drack.getPeq(ob.BandHigh)
    peqHigh.disable()
    print("Disabling High band EQ")
    drack.setPeq(ob.BandHigh, peqHigh)
