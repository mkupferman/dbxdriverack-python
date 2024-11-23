#!/usr/bin/env python3

"""
Connects to a single DriveRack PA2 on the network
Print whether output High-Left is muted
Mutes all outputs
Restores the previous mute states
Mutes all outputs again
Unmutes Low-Left and both High outputs
"""

import time

import dbxdriverack as dr
import dbxdriverack.pa2 as pa2
import dbxdriverack.pa2.outputband as ob

timeout = 3


# Connect and control mutes

with pa2.PA2(debug=False) as drack:
    devices = drack.discoverDevices(timeout=timeout)
    if len(devices) != 1:
        raise Exception("Did not find exactly 1 DriveRack PA2 online")
    address = next(iter(devices))[0]
    drack.connect(address)

    # Print the current mute state of High-Left
    print("High-Left is muted:", drack.isMuted(ob.BandHigh, dr.ChannelLeft))

    # Mute all outputs, preserving the current mute states
    drack.bulkMute(dr.CmdMuteAll, updateState=False)

    # Perform some actions here that might created unwanted noise
    time.sleep(2)

    # Restore the previous mute states
    drack.bulkMute(dr.CmdMuteRestore)

    # Time passes, a show happens, etc.
    time.sleep(2)

    # Mute all outputs and update mute states to reflect the new state
    drack.bulkMute(dr.CmdMuteAll)

    time.sleep(2)
    # Unmute Low-Left and both High outputs
    drack.muteOutput(ob.BandLow, dr.ChannelLeft, False)
    drack.muteOutput(ob.BandHigh, dr.ChannelLeft, False)
    drack.muteOutput(ob.BandHigh, dr.ChannelRight, False)
