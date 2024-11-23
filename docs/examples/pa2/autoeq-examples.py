#!/usr/bin/env python3

"""
Connects to a single DriveRack PA2 on the network.
Get the current Auto EQ
Leave filter 1 as it is, change a few others.
Waits a couple seconds and toggles back to the last "auto" EQ.
Watis a couple more seconds and toggles back to the manual EQ.
"""

import time

import dbxdriverack.pa2 as pa2
import dbxdriverack.pa2.autoeq as aeq

timeout = 3

# Connect and apply

with pa2.PA2(debug=False) as drack:
    devices = drack.discoverDevices(timeout=timeout)
    if len(devices) != 1:
        raise Exception("Did not find exactly 1 DriveRack PA2 online")
    address = next(iter(devices))[0]
    drack.connect(address)

    # get the current Auto EQ & save filter 1
    autoEq = drack.getAeq()
    print("Current Auto EQ:", autoEq)
    filter1 = autoEq.getFilter(1)

    # create a new Auto EQ
    autoEq = aeq.PA2AutoEq()

    # retain the old filter 1
    autoEq.addFilter(filter1)

    # add a few new bands
    autoEqFilter2 = aeq.PA2AutoEqFilter(aeq.Bell, 100, -6, 10)
    autoEqFilter3 = aeq.PA2AutoEqFilter(aeq.Bell, 200, -3, 8)
    autoEqFilter4 = aeq.PA2AutoEqFilter(aeq.LowShelf, 600, 3, 5)
    autoEqFilter5 = aeq.PA2AutoEqFilter(aeq.HighShelf, 10000, -6, 3.5)
    autoEq.addFilter(autoEqFilter2)
    autoEq.addFilter(autoEqFilter3)
    autoEq.addFilter(autoEqFilter4)
    autoEq.addFilter(autoEqFilter5)
    autoEq.enable()

    drack.setAeq(autoEq)

    time.sleep(2)

    drack.aeqChangeMode(aeq.ModeAuto)

    time.sleep(2)

    drack.aeqChangeMode(aeq.ModeManual)
