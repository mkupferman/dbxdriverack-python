#!/usr/bin/env python3

"""
Connects to a single DriveRack PA2 on the network.
Prints the current input delay settings.
Sets delay to 10 ms
Waits a couple seconds, refreshes state, and increases delay by +10 ms.
"""

import time

import dbxdriverack.pa2 as pa2

timeout = 3

# Connect and apply

with pa2.PA2(debug=False) as drack:
    devices = drack.discoverDevices(timeout=timeout)
    if len(devices) != 1:
        raise Exception("Did not find exactly 1 DriveRack PA2 online")
    address = next(iter(devices))[0]
    drack.connect(address)

    indelay = drack.getInputDelay()
    print(indelay)

    # Create new input delay settings
    indelay.setDelay(10)
    indelay.enable()
    drack.setInputDelay(indelay)

    time.sleep(2)

    # update the input delay settings in case they changed
    indelay = drack.getInputDelay()

    # increase by 10 ms
    indelay.setDelay(indelay.getDelay() + 10)
    drack.setInputDelay(indelay)
