#!/usr/bin/env python3

"""Protocol and common functions for connecting to and
controlling the dbx DriveRack series of devices.
"""

import re
from typing import Any

# Constants

## General
AuthAdmin = "administrator"
AuthAdminDefaultPass = "administrator"
PolarityNormal = "Normal"
PolarityInverted = "Inverted"
ChannelLeft = "Left"
ChannelRight = "Right"
ChannelsStereo = "Stereo"

## Python API commands
CmdMuteAll = "MuteAll"
CmdUnmuteAll = "UnmuteAll"
CmdMuteRefresh = "MuteRefresh"
CmdMuteRestore = "MuteRestore"


## Protocol
ProtoHello = "HiQnet Console"
ProtoAttr = "AT"
ProtoValues = "SV"
ProtoConnect = "connect"
ProtoError = "error"
ProtoConnectAck = "connect logged in as"
ProtoConnectFail = f"{ProtoError} could not connect as"
ProtoGet = "get"
ProtoGetAsync = "asyncget"
ProtoSet = "set"
ProtoSub = "sub"
ProtoSubResp = "subr"
ProtoUnsub = "unsub"
ProtoList = "ls"
ProtoListEnd = "endls"

dB2float_re = re.compile(r"(-?\d+(?:\.\d+)?)\s*dB")
freq2Hz_re = re.compile(r"(\d+(?:\.\d+)?)\s*(k?Hz)")
time2sec_re = re.compile(r"(\d+(?:\.\d+)?)\s*(m?s)(?:/.+)?")
percent2float_re = re.compile(r"(\d+(?:\.\d+)?)\s*%")
ratio2numerator_re = re.compile(r"([^:]+):(.+)")


def dB2float(dB: str) -> float:
    """Converts a dB string (e.g. "-10dB", "0 dB") to a float

    Parameters
    ----------
    dB : str
        String representation of a dB value

    Returns
    -------
    float
        Numeric representation of the dB value

    Raises
    ------
    ValueError
        Unable to parse the dB value
    """

    match = dB2float_re.match(dB)
    if not match:
        raise ValueError(f"Invalid dB value {dB}")

    return float(match.group(1))


def freq2Hz(freq: str) -> float:
    """Converts an audio frequency string to a float (in Hz)

    Parameters
    ----------
    freq : str
        Frequency string (e.g. "1 kHz", "300Hz")

    Returns
    -------
    float
        Numeric representation of the frequency in Hz

    Raises
    ------
    ValueError
        Unable to parse the frequency value
    """

    match = freq2Hz_re.match(freq)
    if not match:
        raise ValueError(f"Invalid frequency value {freq}")

    value = float(match.group(1))
    unit = match.group(2)

    if unit == "kHz":
        value *= 1000

    return value


def percent2float(percent: str, multiplier: int = 1) -> float:
    """Converts a percentage string to a float

    Parameters
    ----------
    percent : str
        Percentage string (e.g. "10%", "100 %")
    multiplier : int, optional
        Multiplier for the percentage, by default 1

    Returns
    -------
    float
        Numeric representation of the percentage (e.g. 0.1, 1.0)

    Raises
    ------
    ValueError
        Unable to parse the percentage value
    """

    match = percent2float_re.match(percent)
    if not match:
        raise ValueError(f"Invalid percentage value {percent}")

    return float(match.group(1)) / 100 * multiplier


def time2sec(time: str) -> float:
    """Converts a time string to a float (in seconds)

    Parameters
    ----------
    time : str
        Time string (e.g. "10ms", "1 s")

    Returns
    -------
    float
        Numeric representation of the time in seconds

    Raises
    ------
    ValueError
        Unable to parse the time value
    """

    match = time2sec_re.match(time)
    if not match:
        raise ValueError(f"Invalid time value {time}")

    value = float(match.group(1))
    unit = match.group(2)

    if unit == "ms":
        value /= 1000

    return value


def ratio2numerator(ratio: str) -> str:
    """Extracts the numerator from a ratio string

    Parameters
    ----------
    ratio : str
        Ratio string (e.g. "2:1", "Inf:1")

    Returns
    -------
    str
        Numerator of the ratio

    Raises
    ------
    ValueError
        Unable to parse the ratio value
    """

    match = ratio2numerator_re.match(ratio)
    if not match:
        raise ValueError(f"Invalid ratio value {ratio}")

    return match.group(1)


class CmdBuilder:
    """Factory base class for generating commands to send to a DriveRack device
    over the network. Specific functions of a specific DriceRack should
    override the _generateCmd() method to implement the specific protocols.
    """

    def __init__(self, action: str, target: str, **kwargs: Any) -> None:
        self.action = action
        self.target = target
        self.kwargs = kwargs
        self.command = [action]
        self.isPercent = False
        self.pct = ""  # percentage sign

        if "percent" in kwargs:
            self._percent(bool(kwargs["percent"]))

    def _addArg(self, arg: str) -> None:
        self.command.append(arg)

    def _generateCmd(self) -> None:
        # Overwrite this method in child classes
        pass

    def _percent(self, value: bool) -> None:
        if value:
            self.pct = "\\%"
            self.isPercent = True
        else:
            self.pct = ""
            self.isPercent = False

    def get(self) -> list[str]:
        self._generateCmd()
        return [str(v) for v in self.command]
