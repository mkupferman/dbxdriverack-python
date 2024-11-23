#!/usr/bin/env python3

"""
Connects to a single DriveRack PA2 on the network.
Prints the current crossover settings.
Creates 3 crossover bands and sets them if the current configuration supports them.
Waits a couple seconds, refreshes state, and flips the polarity of the high band.
"""

import time

import dbxdriverack as dr
import dbxdriverack.pa2 as pa2
import dbxdriverack.pa2.crossover as xo

timeout = 3


# Create 3 crossover bands

xoverHigh = xo.PA2CrossoverBand()
xoverHigh.setPolarity(dr.PolarityNormal)
xoverHigh.setHpfType(xo.XoverLR24)
xoverHigh.setHpfFreq(1200)
xoverHigh.setLpfType(xo.XoverBW6)
xoverHigh.setLpfFreq(xo.XoverFreqOut)
xoverHigh.setGain(3.5)

xoverMid = xo.PA2CrossoverBand()
xoverMid.setPolarity(dr.PolarityNormal)
xoverMid.setLpfType(xo.XoverLR24)
xoverMid.setLpfFreq(1200)
xoverMid.setHpfType(xo.XoverLR48)
xoverMid.setHpfFreq(100)
xoverMid.setGain(-1.5)

xoverLow = xo.PA2CrossoverBand()
xoverLow.setPolarity(dr.PolarityInverted)
xoverLow.setLpfType(xo.XoverLR48)
xoverLow.setLpfFreq(100)
xoverLow.setHpfType(xo.XoverBW6)
xoverLow.setHpfFreq(xo.XoverFreqOut)
xoverLow.setGain(6)


# Connect and apply

with pa2.PA2(debug=False) as drack:
    devices = drack.discoverDevices(timeout=timeout)
    if len(devices) != 1:
        raise Exception("Did not find exactly 1 DriveRack PA2 online")
    address = next(iter(devices))[0]
    drack.connect(address)

    crossover = drack.getCrossover()
    print(crossover)

    crossover.setHigh(xoverHigh)


    if drack.hasMids():
        print("Mid band exists: Setting crossover")
        crossover.setMid(xoverMid)
    if drack.hasSubs():
        print("Sub band exists: Setting crossover")
        crossover.setLow(xoverLow)

    drack.setCrossover(crossover)

    time.sleep(2)

    crossover = drack.getCrossover()
    xoverHigh = crossover.getHigh()
    polarityHigh = xoverHigh.getPolarity()
    xoverHigh.setPolarity(
        dr.PolarityInverted if polarityHigh == dr.PolarityNormal else dr.PolarityNormal
    )
    crossover.setHigh(xoverHigh)
    drack.setCrossover(crossover)
