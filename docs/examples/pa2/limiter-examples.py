#!/usr/bin/env python3

"""
Connects to a single DriveRack PA2 on the network.
Prints the current High band limiter settings.
Creates 3 limiters and sets them if the current configuration supports them.
Waits a couple seconds, refreshes state, decreases the High band limiter threshold by -3 dB.
"""

import time

import dbxdriverack.pa2 as pa2
import dbxdriverack.pa2.limiter as lim
import dbxdriverack.pa2.outputband as ob

timeout = 3


# Create 3 limiters

limiterHigh = lim.PA2Limiter()
limiterHigh.setThreshold(-3)
limiterHigh.setOverEasy(1)
limiterHigh.enable()

limiterMid = lim.PA2Limiter()
limiterMid.setThreshold(-50)
limiterMid.setOverEasy(0)
limiterMid.disable()

limiterLow = lim.PA2Limiter()
limiterLow.setThreshold(0)
limiterLow.setOverEasy(5)
limiterLow.enable()

# Connect and apply

with pa2.PA2(debug=False) as drack:
    devices = drack.discoverDevices(timeout=timeout)
    if len(devices) != 1:
        raise Exception("Did not find exactly 1 DriveRack PA2 online")
    address = next(iter(devices))[0]
    drack.connect(address)

    currentHigh = drack.getLimiter(ob.BandHigh)
    print(currentHigh)

    drack.setLimiter(ob.BandHigh, limiterHigh)

    if drack.hasMids():
        print("Mid band exists: Setting limiter")
        drack.setLimiter(ob.BandMid, limiterMid)

    if drack.hasSubs():
        print("Sub band exists: Setting limiter")
        drack.setLimiter(ob.BandLow, limiterLow)

    time.sleep(2)

    limiterHigh = drack.getLimiter(ob.BandHigh)
    limiterHigh.setThreshold(limiterHigh.getThreshold() - 3)
    drack.setLimiter(ob.BandHigh, limiterHigh)
