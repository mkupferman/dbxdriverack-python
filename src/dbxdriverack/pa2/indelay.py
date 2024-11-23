#!/usr/bin/env python3

import dbxdriverack as dr

# Constants

## Input Delay
Enabled = "On"
Disabled = "Off"
MinTime = 0
MaxTime = 100  # milliseconds

## Protocol
InputDelay = "\\\\Preset\\Back Line Delay"
State = "Delay"
Time = "Amount"  # seconds


class PA2InputDelay:
    """Represents the input delay block settings in the DriveRack PA2.
    None of the methods directly affect a live device.

    Attributes
    ----------
    delay : float
        Delay in milliseconds
    enabled : bool
        Whether the input delay is enabled

    Constants
    ---------
    Enabled : str
        On state for Input Delay block
    Disabled : str
        Off state for Input Delay block
    MinTime : int
        Minimum delay in milliseconds
    MaxTime : int
        Maximum delay in milliseconds
    """

    def __init__(self) -> None:
        """
        Parameters
        ----------
        None

        Delay is initialized to 0ms and disabled.
        """

        self.delay: float = 0.0  # milliseconds
        self.enabled: bool = False

    def setDelay(self, delay: float) -> None:
        """Set the delay in milliseconds.

        Parameters
        ----------
        delay : float
            Delay in milliseconds

        Raises
        ------
        ValueError
            Delay out of range (0-100ms)
        """

        if not (MinTime <= delay <= MaxTime):
            raise ValueError("Delay out of range")
        self.delay = delay

    def enable(self) -> None:
        """Enable the input delay."""

        self.enabled = True

    def disable(self) -> None:
        """Disable the input delay."""

        self.enabled = False

    def getDelay(self) -> float:
        """Get the delay in milliseconds.

        Returns
        -------
        float
            Delay in milliseconds
        """

        return self.delay

    def isEnabled(self) -> bool:
        """Get the enabled state of the input delay.

        Returns
        -------
        bool
            True if enabled, False if disabled
        """

        return self.enabled

    def __str__(self) -> str:
        return f"Input Delay: {self.enabled}, {self.delay}ms"


class CmdBuilder(dr.CmdBuilder):
    """Subclass of the CmdBuilder network protocol factory for DriveRack PA2."""

    def _generateCmd(self) -> None:
        if self.target in [Time, State]:
            if self.command[0] == dr.ProtoGet:
                self._addArg(f"{InputDelay}\\{dr.ProtoValues}\\{self.target}")
            elif self.command[0] == dr.ProtoSet:
                if "value" not in self.kwargs:
                    raise ValueError("Value must be specified for input delay commands")
                value = self.kwargs["value"]

                if self.target == State:
                    if type(value) != bool:
                        raise ValueError(
                            "Value must be boolean for input delay enable/disable"
                        )
                    self._addArg(f"{InputDelay}\\{dr.ProtoValues}\\{State}")
                    self._addArg(Enabled if value else Disabled)
                elif self.target == Time:
                    if not (MinTime <= value <= MaxTime):
                        raise ValueError(
                            f"Time must be in the range {MinTime} to {MaxTime}"
                        )
                    self._addArg(f"{InputDelay}\\{dr.ProtoValues}\\{Time}")
                    self._addArg(f"{(value/1000.0):.4f}")
