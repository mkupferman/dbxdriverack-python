#!/usr/bin/env python3

import dbxdriverack as dr

# Constants

## Subharmonic Synth
Enabled = "On"
Disabled = "Off"

## Protocol
Subharmonic = "\\\\Preset\\SubharmonicSynth"
Enable = "SubharmonicSynth"
Harmonics = "Subharmonics"
Lows = "Synthesis Level 24-36Hz"
Highs = "Synthesis Level 36-56Hz"


class PA2Subharmonic:
    """Represents the Subharmonic Synthesis section of a PA2 device.
    None of the methods directly affect a live device.

    Attributes
    ----------
    enabled : bool
        Whether the subharmonic synthesis is enabled
    harmonics : float
        Master percentage of subharmonics
    lows : float
        Percentage of subharmonics in the range 24-36Hz
    highs : float
        Percentage of subharmonics in the range 36-56Hz

    Constants
    ---------
    Enabled : str
        On state for the Subharmonic Synthesis block
    Disabled : str
        Off state for the Subharmonic Synthesis block
    """

    def __init__(self, enabled: bool = True) -> None:
        """
        Parameters
        ----------
        enabled : bool, optional
            Enable the subharmonic synthesis, by default True

        Initialized with enabled state and 50% for all synthesis levels.
        """

        self.enabled: bool = enabled
        self.harmonics: float = 50.0
        self.lows: float = 50.0
        self.highs: float = 50.0

    def setHarmonics(self, percentage: float) -> None:
        """Set the master percentage of subharmonics.

        Parameters
        ----------
        percentage : float
            Percentage of subharmonics (0-100)

        Raises
        ------
        ValueError
            Percentage out of range (0-100)
        """

        if not (0 <= percentage <= 100):
            raise ValueError("Percentage must be in the range 0 to 100")
        self.harmonics = percentage

    def setLows(self, percentage: float) -> None:
        """Set the percentage of subharmonics in the range 24-36Hz.

        Parameters
        ----------
        percentage : float
            Percentage of subharmonics (0-100)

        Raises
        ------
        ValueError
            Percentage out of range (0-100)
        """

        if not (0 <= percentage <= 100):
            raise ValueError("Percentage must be in the range 0 to 100")
        self.lows = percentage

    def setHighs(self, percentage: float) -> None:
        """Set the percentage of subharmonics in the range 36-56Hz.

        Parameters
        ----------
        percentage : float
            Percentage of subharmonics (0-100)

        Raises
        ------
        ValueError
            Percentage out of range (0-100)
        """

        if not (0 <= percentage <= 100):
            raise ValueError("Percentage must be in the range 0 to 100")
        self.highs = percentage

    def enable(self) -> None:
        """Enable the subharmonic synthesis."""

        self.enabled = True

    def disable(self) -> None:
        """Disable the subharmonic synthesis."""

        self.enabled = False

    def getHarmonics(self) -> float:
        """Get the master percentage of subharmonics.

        Returns
        -------
        float
            Percentage of subharmonics (0-100)
        """

        return self.harmonics

    def getLows(self) -> float:
        """Get the percentage of subharmonics in the range 24-36Hz.

        Returns
        -------
        float
            Percentage of subharmonics (0-100)
        """

        return self.lows

    def getHighs(self) -> float:
        """Get the percentage of subharmonics in the range 36-56Hz.

        Returns
        -------
        float
            Percentage of subharmonics (0-100)
        """

        return self.highs

    def isEnabled(self) -> bool:
        """Get the enable state of the subharmonic synthesis.

        Returns
        -------
        bool
            True if enabled, False if disabled
        """

        return self.enabled

    def __str__(self) -> str:
        return f"Subharmonic Synth: Enabled:{self.enabled}, Master:{self.harmonics}%, Low:{self.lows}%, High:{self.highs}%"


class CmdBuilder(dr.CmdBuilder):
    """Subclass of the CmdBuilder network protocol factory for DriveRack PA2."""

    def _generateCmd(self) -> None:
        if self.target in [Subharmonic, Harmonics, Lows, Highs, Enable]:
            if self.command[0] == dr.ProtoGet:
                self._addArg(f"{Subharmonic}\\{dr.ProtoValues}\\{self.target}")
            elif self.command[0] == dr.ProtoSet:
                if "value" not in self.kwargs:
                    raise ValueError(
                        f"Value must be specified for Subharmonic target {self.target}"
                    )
                value = self.kwargs["value"]

                if self.target == Enable:
                    self._addArg(f"{Subharmonic}\\{dr.ProtoValues}\\{Enable}")
                    self._addArg(Enabled if self.kwargs["value"] else Disabled)
                else:
                    self._addArg(f"{Subharmonic}\\{dr.ProtoValues}\\{self.target}")
                    self._addArg(value)
