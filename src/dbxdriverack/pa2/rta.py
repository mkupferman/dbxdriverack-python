#!/usr/bin/env python3

import dbxdriverack as dr

# Constants

## Real Time Analyzer
Slow = "Slow"
Fast = "Fast"
OffsetMin = 0
OffsetMax = 40

## Protocol
RTA = "\\\\Preset\\RTA"
Rate = "Rate"
Offset = "Gain"


class PA2Rta:
    """Represents the Real Time Analyzer (RTA) section of a PA2 device.
    None of the methods directly affect a live device.

    Attributes
    ----------
    rate : str
        The rate of the RTA (Slow or Fast)
    offset : float
        The graph offset of the RTA in dB

    Constants
    ---------
    Slow : str
        Slow rate for the RTA
    Fast : str
        Fast rate for the RTA
    OffsetMin : int
        Minimum offset in dB
    OffsetMax : int
        Maximum offset in dB
    """

    def __init__(self) -> None:
        """
        Parameters
        ----------
        None

        Initialized with Slow rate and 0dB offset.
        """

        self.rate: str = Slow
        self.offset: float = 0.0

    def setRate(self, rate: str) -> None:
        """Set the rate of the RTA.

        Parameters
        ----------
        rate : str
            Rate of the RTA.
            One of rta.Slow or rta.Fast

        Raises
        ------
        ValueError
            Invalid rate
        """

        if rate not in [Slow, Fast]:
            raise ValueError("Invalid rate")
        self.rate = rate

    def setOffset(self, offset: float) -> None:
        """Set the graph offset of the RTA.

        Parameters
        ----------
        offset : float
            Offset in dB

        Raises
        ------
        ValueError
            Offset out of range (0-40dB)
        """

        if not (OffsetMin <= offset <= OffsetMax):
            raise ValueError("Offset out of range")
        self.offset = offset

    def getRate(self) -> str:
        """Get the rate of the RTA.

        Returns
        -------
        str
            Rate of the RTA.
            One of rta.Slow or rta.Fast.
        """

        return self.rate

    def getOffset(self) -> float:
        """Get the graph offset of the RTA.

        Returns
        -------
        float
            Offset in dB
        """

        return self.offset

    def __str__(self) -> str:
        return f"RTA: {self.rate}, {self.offset}dB"


class CmdBuilder(dr.CmdBuilder):
    """Subclass of the CmdBuilder network protocol factory for DriveRack PA2."""

    def _generateCmd(self) -> None:
        if self.target in [Rate, Offset]:
            if self.command[0] == dr.ProtoGet:
                self._addArg(f"{RTA}\\{dr.ProtoValues}\\{self.target}")
            else:
                if "value" not in self.kwargs:
                    raise ValueError("Value must be specified for RTA commands")
                value = self.kwargs["value"]

                if self.target == Rate:
                    if value not in [Slow, Fast]:
                        raise ValueError("Invalid rate")
                    self._addArg(f"{RTA}\\{dr.ProtoValues}\\{Rate}")
                    self._addArg(value)
                elif self.target == Offset:
                    if not (OffsetMin <= value <= OffsetMax):
                        raise ValueError(
                            f"Offset must be in the range {OffsetMin} to {OffsetMax}"
                        )
                    self._addArg(f"{RTA}\\{dr.ProtoValues}\\{Offset}")
                    self._addArg(value)
