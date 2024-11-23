#!/usr/bin/env python3

import dbxdriverack as dr
import dbxdriverack.pa2.outputband as ob

# Constants

## Limiter
Enabled = "On"
Disabled = "Off"
MinThresh = -60
MaxThresh = 0
MinOverEasy = 0
MaxOverEasy = 10
OverEasyOff = "Off"

## Protocol
High = "\\\\Preset\\High Outputs Limiter"
Mid = "\\\\Preset\\Mid Outputs Limiter"
Low = "\\\\Preset\\Low Outputs Limiter"
State = "Limiter"
Thresh = "Threshold"
OverEasy = "OverEasy"


class PA2Limiter:
    """Represents a PA2 Limiter block
    The PA2 can have up to 3 limiters, one for each output band (Low, Mid, High)
    and this object represents one of those limiters, which can be applied to
    one of the available output bands of a PA2 device.
    None of the methods directly affect a live device.

    Attributes
    ----------
    enabled : bool
        Whether the limiter is enabled
    threshold : float
        The threshold in dB
    overEasy : int
        The OverEasy value

    Constants
    ---------
    Enabled : str
        On state for the Limiter block
    Disabled : str
        Off state for the Limiter block
    MinThresh : int
        Minimum threshold in dB
    MaxThresh : int
        Maximum threshold in dB
    MinOverEasy : int
        Minimum OverEasy value
    MaxOverEasy : int
        Maximum OverEasy value
    """

    def __init__(self) -> None:
        """
        Parameters
        ----------
        None

        Initialized with default values:
            enabled: False
            threshold: 0
            overEasy: 0 (Off)
        """

        self.enabled: bool = False
        self.threshold: float = 0.0
        self.overEasy: int = 0  # 0 = Off

    def setThreshold(self, threshold: float) -> None:
        """Set the threshold value

        Parameters
        ----------
        threshold : float
            The threshold value in dB

        Raises
        ------
        ValueError
            Threshold out of range (-60 to 0)
        """

        if not (MinThresh <= threshold <= MaxThresh):
            raise ValueError("Threshold out of range")
        self.threshold = threshold

    def setOverEasy(self, overEasy: int) -> None:
        """Set the OverEasy value

        Parameters
        ----------
        overEasy : int
            OverEasy value. 0 is Off.

        Raises
        ------
        ValueError
            OverEasy out of range (0-10)
        """

        if not (MinOverEasy <= overEasy <= MaxOverEasy):
            raise ValueError("OverEasy out of range")
        self.overEasy = overEasy

    def enable(self) -> None:
        """Enable the limiter"""

        self.enabled = True

    def disable(self) -> None:
        """Disable the limiter"""

        self.enabled = False

    def getThreshold(self) -> float:
        """Get the threshold value

        Returns
        -------
        float
            The threshold value in dB
        """

        return self.threshold

    def getOverEasy(self) -> int:
        """Get the OverEasy value

        Returns
        -------
        int
            OverEasy value
        """

        return self.overEasy

    def isEnabled(self) -> bool:
        """Enable state of the limiter

        Returns
        -------
        bool
            True if enabled, False if disabled
        """

        return self.enabled

    def __str__(self) -> str:
        return f"Enabled: {self.enabled}, Threshold: {self.threshold:.2f}, OverEasy: {self.overEasy}"


class CmdBuilder(dr.CmdBuilder):
    """Subclass of the CmdBuilder network protocol factory for DriveRack PA2."""

    def _generateCmd(self) -> None:
        if self.target in [Thresh, OverEasy, State]:
            if "band" not in self.kwargs:
                raise ValueError("Band must be specified for limiter commands")
            band = self.kwargs["band"]
            if band not in [ob.BandLow, ob.BandMid, ob.BandHigh]:
                raise ValueError("Invalid band")
            if band == ob.BandLow:
                limiterTarget = Low
            elif band == ob.BandMid:
                limiterTarget = Mid
            elif band == ob.BandHigh:
                limiterTarget = High
            else:
                raise ValueError("Invalid band")

            if "value" not in self.kwargs:
                raise ValueError("Value must be specified for limiter commands")
            value = self.kwargs["value"]

            if self.target == State:
                if type(value) != bool:
                    raise ValueError("Value must be boolean for State")
                value = Enabled if value else Disabled
            elif self.target in [Thresh, OverEasy]:
                value = f"{(value):.2f}"

            self._addArg(f"{limiterTarget}\\SV\\{self.target}")
            self._addArg(value)
