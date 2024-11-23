#!/usr/bin/env python3

"""
Connects to a single DriveRack PA2 on the network.
Prints the current subharmonic settings.
Sets subharmonics at 25%, 24-36Hz at 75%, and 36-56Hz at 60%.
Waits a couple seconds, refreshes state, and decrements harmonics by 10%.
"""

import time

import dbxdriverack.pa2 as pa2
import dbxdriverack.pa2.subharmonic as sub

timeout = 3


# Create subharmonics settings
subharmonic = sub.PA2Subharmonic()
subharmonic.setHarmonics(25)
subharmonic.setLows(75)
subharmonic.setHighs(60)
subharmonic.enable()

# Connect and apply

with pa2.PA2(debug=False) as drack:
    devices = drack.discoverDevices(timeout=timeout)
    if len(devices) != 1:
        raise Exception("Did not find exactly 1 DriveRack PA2 online")
    address = next(iter(devices))[0]
    drack.connect(address)

    currentSubharmonic = drack.getSubharmonic()
    print(currentSubharmonic)

    drack.setSubharmonic(subharmonic)

    subharmonic = drack.getSubharmonic()

    time.sleep(2)

    subharmonic.setHarmonics((subharmonic.getHarmonics()) - 10)
    drack.setSubharmonic(subharmonic)
