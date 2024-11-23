#!/usr/bin/env python3

import dbxdriverack as dr
import dbxdriverack.pa2.outputband as ob

# Constants

## Output Delay
Enabled = "On"
Disabled = "Off"
MinDelay = 0
MaxDelay = 10000


## Protocol
High = "\\\\Preset\\High Outputs Delay"
Mid = "\\\\Preset\\Mid Outputs Delay"
Low = "\\\\Preset\\Low Outputs Delay"
State = "Delay"
Time = "Amount"  # seconds


class PA2OutputDelay:
    """Represents a PA2 Output (Alignment) Delay block.
    The PA2 can have up to 3 output delays, one for each output band (Low, Mid, High)
    and this object represents one of those delays, which can be applied to
    one of the available output bands of a PA2 device.
    None of the methods directly affect a live device.

    Attributes
    ----------
    delay : float
        The delay in milliseconds
    enabled : bool
        Whether the delay is enabled

    Constants
    ---------
    Enabled : str
        On state for the Delay block
    Disabled : str
        Off state for the Delay block
    MinDelay : int
        Minimum delay in milliseconds
    MaxDelay : int
        Maximum delay in milliseconds
    """

    def __init__(self) -> None:
        """
        Parameters
        ----------
        None

        Initialized with 0ms delay and disabled.
        """

        self.delay: float = 0
        self.enabled: bool = False

    def setDelay(self, delay: float) -> None:
        """Set the delay in milliseconds

        Parameters
        ----------
        delay : float
            Delay in milliseconds

        Raises
        ------
        ValueError
            Delay out of range (0-10000ms)
        """

        if not (MinDelay <= delay <= MaxDelay):
            raise ValueError("Delay out of range")
        self.delay = delay

    def enable(self) -> None:
        """Enable the delay"""

        self.enabled = True

    def disable(self) -> None:
        """Disable the delay"""

        self.enabled = False

    def getDelay(self) -> float:
        """Get the delay in milliseconds

        Returns
        -------
        float
            Delay in milliseconds
        """

        return self.delay

    def isEnabled(self) -> bool:
        """Enable state of the delay

        Returns
        -------
        bool
            True if enabled, False if disabled
        """

        return self.enabled

    def __str__(self) -> str:
        return f"Output Delay: {self.enabled}, {self.delay}ms"


class CmdBuilder(dr.CmdBuilder):
    """Subclass of the CmdBuilder network protocol factory for DriveRack PA2."""

    def _generateCmd(self) -> None:
        if self.target in [Time, State]:
            if "band" not in self.kwargs:
                raise ValueError("Band must be specified for output delay commands")
            band = self.kwargs["band"]
            if band not in [ob.BandLow, ob.BandMid, ob.BandHigh]:
                raise ValueError("Invalid band")
            if band == ob.BandLow:
                outputDelayTarget = Low
            elif band == ob.BandMid:
                outputDelayTarget = Mid
            elif band == ob.BandHigh:
                outputDelayTarget = High
            else:
                raise ValueError("Invalid band")

            if "value" not in self.kwargs:
                raise ValueError("Value must be specified for output delay commands")
            value = self.kwargs["value"]

            if self.target == State:
                if type(value) != bool:
                    raise ValueError("Value must be boolean for State")
                value = Enabled if value else Disabled
            elif self.target == Time:
                value = f"{(value/1000.0):.4f}"

            self._addArg(f"{outputDelayTarget}\\{dr.ProtoValues}\\{self.target}")
            self._addArg(value)
