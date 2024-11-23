#!/usr/bin/env python3

"""
Connects to a single DriveRack PA2 on the network.
Prints the current generator settings.
Sets the generator to white noise at -20 dB.
Waits a couple seconds and sets the generator to pink noise at -12 dB.
Waits a couple seconds and turns the generator off.
"""

import time

import dbxdriverack.pa2 as pa2
import dbxdriverack.pa2.generator as gen

timeout = 3


# Create generator settings

generator = gen.PA2Generator()
generator.setMode(gen.ModeWhite)
generator.setLevel(-20)

# Connect and apply

with pa2.PA2(debug=False) as drack:
    devices = drack.discoverDevices(timeout=timeout)
    if len(devices) != 1:
        raise Exception("Did not find exactly 1 DriveRack PA2 online")
    address = next(iter(devices))[0]
    drack.connect(address)

    generator = drack.getGenerator()
    print(generator)

    drack.setGenerator(generator)

    time.sleep(2)

    generator.setMode(gen.ModePink)
    generator.setLevel(-12)
    drack.setGenerator(generator)

    time.sleep(2)

    generator.setMode(gen.ModeOff)
    drack.setGenerator(generator)
