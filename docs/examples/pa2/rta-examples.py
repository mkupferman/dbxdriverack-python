#!/usr/bin/env python3

"""
Connects to a single DriveRack PA2 on the network.
Prints the current rate setting (Slow or Fast) and offset.
Sets the RTA to "fast" with an offset of 20 dB.
Waits a couple seconds and sets the RTA to "slow" with an offset of 0 dB.
"""

import time

import dbxdriverack.pa2 as pa2
import dbxdriverack.pa2.rta as rta

timeout = 3

# Connect and apply

with pa2.PA2(debug=False) as drack:
    devices = drack.discoverDevices(timeout=timeout)
    if len(devices) != 1:
        raise Exception("Did not find exactly 1 DriveRack PA2 online")
    address = next(iter(devices))[0]
    drack.connect(address)

    analyzer = drack.getRta()
    print(analyzer)

    analyzer = rta.PA2Rta()
    analyzer.setRate(rta.Fast)
    analyzer.setOffset(20)

    drack.setRta(analyzer)

    time.sleep(2)

    analyzer.setRate(rta.Slow)
    analyzer.setOffset(0)
    drack.setRta(analyzer)
