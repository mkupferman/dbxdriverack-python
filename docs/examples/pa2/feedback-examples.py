#!/usr/bin/env python3

"""
Connects to a single DriveRack PA2 on the network.
Prints the current AFS settings.
Sets AFS in Fixed/Speech modes with 4 fixed filters and 10s lift time.
Waits a couple seconds, refreshes state, and decrements fixed filters by 1.
Waits a couple seconds and switches to Live/Music mode.
Waits a couple seconds and lifts live filters.
Waits a couple seconds and clears live filters.
Waits a couple seconds and clears all filters.
"""

import time

import dbxdriverack.pa2 as pa2
import dbxdriverack.pa2.feedback as afs

timeout = 3


# Define the AFS settings


# Connect and apply

with pa2.PA2(debug=False) as drack:
    devices = drack.discoverDevices(timeout=timeout)
    if len(devices) != 1:
        raise Exception("Did not find exactly 1 DriveRack PA2 online")
    address = next(iter(devices))[0]
    drack.connect(address)

    feedback = drack.getAfs()
    print(feedback)

    # build a new feedback object
    feedback = afs.PA2Feedback(enabled=True)
    feedback.setMode(afs.ModeFixed)
    feedback.setType(afs.TypeSpeech)
    feedback.setFixedFilters(4)
    feedback.setLiftTime(10)
    drack.setAfs(feedback)

    time.sleep(2)

    feedback = drack.getAfs()
    feedback.setFixedFilters(feedback.getFixedFilters() - 1)
    drack.setAfs(feedback)

    time.sleep(2)

    drack.afsLiveLift()

    time.sleep(2)

    drack.afsClearLive()

    time.sleep(2)

    drack.afsClearAll()
