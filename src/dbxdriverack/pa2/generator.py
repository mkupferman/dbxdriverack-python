#!/usr/bin/env python3

import dbxdriverack as dr

# Constants

## Signal Generator
ModeOff = "Off"
ModePink = "Pink"
ModeWhite = "White"
MinLevel = -60
MaxLevel = 0

## Protocol
Generator = "\\\\Preset\\SignalGenerator"
Mode = "Signal Generator"
Level = "Signal Amplitude"


class PA2Generator:
    """Represents the signal generator of a DriveRack PA2.
    None of the methods directly affect a live device.

    Attributes
    ----------
    mode : str
        The mode of the signal generator.
        One of generator.ModeOff, generator.ModePink, generator.ModeWhite.
    level : float
        The level of the signal generator in dB.

    Constants
    ---------
    ModeOff : str
        Off state for Signal Generator block
    ModePink : str
        Pink noise mode for Signal Generator block
    ModeWhite : str
        White noise mode for Signal Generator block
    MinLevel : int
        Minimum level in dB
    MaxLevel : int
        Maximum level in dB
    """

    def __init__(self, mode: str = ModeOff, level: int = MinLevel):
        """
        Parameters
        ----------
        mode : str, optional
            Operation mode, off by default.
            One of generator.ModeOff, generator.ModePink, generator.ModeWhite.
        level : int, optional
            Level in dB, -60 by default.
        """

        self.mode: str = mode
        self.level: float = level

    def setMode(self, mode: str) -> None:
        """Set the operating mode of the signal generator.

        Parameters
        ----------
        mode : str
            Mode of the signal generator.
            One of generator.ModeOff, generator.ModePink, generator.ModeWhite.

        Raises
        ------
        ValueError
            Invalid mode specified
        """

        if mode not in [ModeOff, ModePink, ModeWhite]:
            raise ValueError("Invalid mode")
        self.mode = mode

    def setLevel(self, level: float) -> None:
        """Set the level of the signal generator.

        Parameters
        ----------
        level : float
            Level in dB.

        Raises
        ------
        ValueError
            Level out of range (-60 to 0)
        """

        if not (MinLevel <= level <= MaxLevel):
            raise ValueError("Level out of range")
        self.level = level

    def getMode(self) -> str:
        """Get the mode of the signal generator.

        Returns
        -------
        str
            Mode of the signal generator.
            One of generator.ModeOff, generator.ModePink, generator.ModeWhite.
        """

        return self.mode

    def getLevel(self) -> float:
        """
        Get the level of the signal generator.
        """
        return self.level

    def __str__(self) -> str:
        return f"Signal Generator: {self.mode}, {self.level}dB"


class CmdBuilder(dr.CmdBuilder):
    """Subclass of the CmdBuilder network protocol factory for DriveRack PA2."""

    def _generateCmd(self) -> None:
        if self.target in [Mode, Level]:
            if self.command[0] == dr.ProtoGet:
                self._addArg(f"{Generator}\\{dr.ProtoValues}\\{self.target}")
            elif self.command[0] == dr.ProtoSet:
                if "value" not in self.kwargs:
                    raise ValueError(
                        "Value must be specified for signal generator commands"
                    )
                value = self.kwargs["value"]

                if self.target == Mode:
                    if value not in [ModeOff, ModePink, ModeWhite]:
                        raise ValueError("Invalid mode")
                    self._addArg(f"{Generator}\\{dr.ProtoValues}\\{Mode}")
                    self._addArg(value)
                elif self.target == Level:
                    if not (MinLevel <= value <= MaxLevel):
                        raise ValueError(
                            f"Level must be in the range {MinLevel} to {MaxLevel}"
                        )
                    self._addArg(f"{Generator}\\{dr.ProtoValues}\\{Level}")
                    self._addArg(value)
