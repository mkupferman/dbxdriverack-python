#!/usr/bin/env python3

"""
Connects to a single DriveRack PA2 on the network.
Prints the current compressor settings.
Sets a compressor with a threshold of -20 dB, gain of 2 dB, ratio of 2:1, and OverEasy 2.
Waits a couple seconds and sets ratio to infinity.
Waits a couple seconds, refreshes state, and increases gain by +2 dB.
"""

import time

import dbxdriverack.pa2 as pa2
import dbxdriverack.pa2.compressor as comp

timeout = 3

# Connect and apply

with pa2.PA2(debug=False) as drack:
    devices = drack.discoverDevices(timeout=timeout)
    if len(devices) != 1:
        raise Exception("Did not find exactly 1 DriveRack PA2 online")
    address = next(iter(devices))[0]
    drack.connect(address)

    compressor = drack.getCompressor()
    print(compressor)

    # Replace compressor with new settings
    compressor = comp.PA2Compressor()
    compressor.setThreshold(-20)
    compressor.setGain(2)
    compressor.setRatio(2)
    compressor.setOverEasy(2)
    compressor.enable()
    drack.setCompressor(compressor)

    time.sleep(2)

    compressor.setRatio(comp.RatioBrickwall)
    drack.setCompressor(compressor)

    time.sleep(2)

    compressor = drack.getCompressor()
    compressor.setGain(compressor.getGain() + 2)
    drack.setCompressor(compressor)
