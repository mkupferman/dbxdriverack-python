#!/usr/bin/env python3

import dbxdriverack as dr

# Constants

## Graphic EQ
Enabled = "On"
Disabled = "Off"
ModeFlat = "Flat"
ModeMyBand = "MyBand"
ModeSpeech = "Speech"
ModeVenue = "PerformanceVenue"
ModeDJ = "DJ"
ModeManual = "Manual"  # adjustments made imply Manual mode
MinGain = -12
MaxGain = 12

## Generic Targets
GeqBand = "Band"

## Protocol
Enable = "GraphicEQ"
Mode = "QuickCurve"
GraphicEqSt = "\\\\Preset\\StereoGEQ"
GraphicEqL = "\\\\Preset\\LeftGEQ"
GraphicEqR = "\\\\Preset\\RightGEQ"
Band: dict[int, str] = {
    1: "20 Hz",
    2: "25 Hz",
    3: "31.5 Hz",
    4: "40 Hz",
    5: "50 Hz",
    6: "63 Hz",
    7: "80 Hz",
    8: "100 Hz",
    9: "125 Hz",
    10: "160 Hz",
    11: "200 Hz",
    12: "250 Hz",
    13: "315 Hz",
    14: "400 Hz",
    15: "500 Hz",
    16: "630 Hz",
    17: "800 Hz",
    18: "1.0 kHz",
    19: "1.25 kHz",
    20: "1.6 kHz",
    21: "2.0 kHz",
    22: "2.5 kHz",
    23: "3.15 kHz",
    24: "4.0 kHz",
    25: "5.0 kHz",
    26: "6.3 kHz",
    27: "8.0 kHz",
    28: "10.0 kHz",
    29: "12.5 kHz",
    30: "16.0 kHz",
    31: "20.0 kHz",
}


class PA2Geq:
    """Represents a 31-band graphic equalizer on the DriveRack PA2.
    The PA2 can have one stereo-linked or two independent mono GEQs,
    this object is agnostic to the configuration and these settings
    may be applied to one or the other.
    None of the methods directly affect a live device.

    Attributes
    ----------
    enabled : bool
        Whether the GEQ is enabled
    bands : dict[int, float]
        Dictionary of band gains.
        Key is the band number (1-31), value is the gain in dB.

    Constants
    ---------
    Enabled : str
        On state for Graphic EQ block
    Disabled : str
        Off state for Graphic EQ block
    ModeFlat : str
        Flat mode for Graphic EQ block
    ModeMyBand : str
        My Band mode for Graphic EQ block
    ModeSpeech : str
        Speech mode for Graphic EQ block
    ModeVenue : str
        Performance Venue mode for Graphic EQ block
    ModeDJ : str
        DJ mode for Graphic EQ block
    ModeManual : str
        Manual mode for Graphic EQ block
        This mode is implied after any adjustments are made
    MinGain : int
        Minimum gain in dB
    MaxGain : int
        Maximum gain in dB
    """

    def __init__(self, enabled: bool = True) -> None:
        """
        Parameters
        ----------
        enabled : bool, optional
            Enable or disable the GEQ block, by default True

        All bands are initialized to 0 dB (unity) gain.
        """

        self.enabled: bool = enabled
        self.bands: dict[int, float] = {band: 0.0 for band in Band.keys()}

    def setBand(self, band: int, gain: float) -> None:
        """Set the gain of a band in the GEQ.

        Parameters
        ----------
        band : int
            Band number (1-31)
            Band 1 represents 20 Hz, Band 31 represents 20 kHz
        gain : float
            Gain setting in dB for the band

        Raises
        ------
        ValueError
            Invalid band number or gain out of range
        """

        if band not in Band.keys():
            raise ValueError(f"Invalid band {band}")

        if not (MinGain <= gain <= MaxGain):
            raise ValueError(f"Gain must be in the range {MinGain} to {MaxGain}")

        self.bands[band] = gain

    def enable(self) -> None:
        """Enable the GEQ block."""

        self.enabled = True

    def disable(self) -> None:
        """Disable the GEQ block."""
        self.enabled = False

    def _flatten(self) -> None:
        """Flatten the GEQ to unity gain."""
        self.bands = {band: 0 for band in Band.keys()}

    def isEnabled(self) -> bool:
        """Get the enabled state of the GEQ.

        Returns
        -------
        bool
            True if enabled, False if disabled
        """

        return self.enabled

    def __str__(self) -> str:
        return f"Enabled: {self.enabled}"


class CmdBuilder(dr.CmdBuilder):
    """Subclass of the CmdBuilder network protocol factory for DriveRack PA2."""

    def _generateCmd(self) -> None:
        if "channel" not in self.kwargs:
            raise ValueError(
                f"Channel ({dr.ChannelLeft}, {dr.ChannelRight}, {dr.ChannelsStereo}) must be specified for GEQ commands"
            )
        channel = self.kwargs["channel"]
        if channel == dr.ChannelsStereo:
            geq = GraphicEqSt
        elif channel == dr.ChannelLeft:
            geq = GraphicEqL
        elif channel == dr.ChannelRight:
            geq = GraphicEqR
        else:
            raise ValueError(f"Invalid channel {channel}")

        if self.command[0] == dr.ProtoGet:
            if self.target == GeqBand:
                if "bandNumber" not in self.kwargs:
                    raise ValueError(
                        f"Band number must be specified for GEQ band commands"
                    )
                bandNumber = self.kwargs["bandNumber"]
                if bandNumber not in Band.keys():
                    raise ValueError(f"Invalid band number {bandNumber}")

                self._addArg(f"{geq}\\{dr.ProtoValues}\\{Band[bandNumber]}")
            elif self.target == Enable:
                self._addArg(f"{geq}\\{dr.ProtoValues}\\{Enable}")
        elif self.command[0] == dr.ProtoSet:
            if self.target in [Enable, Mode, GeqBand]:
                if "value" not in self.kwargs:
                    raise ValueError(
                        f"Value must be specified for GEQ target {self.target}"
                    )
                value = self.kwargs["value"]

                if self.target == Mode:
                    if value not in [
                        ModeFlat,
                        ModeMyBand,
                        ModeSpeech,
                        ModeVenue,
                        ModeDJ,
                        ModeManual,
                    ]:
                        raise ValueError(f"Invalid mode {value}")
                    self._addArg(f"{geq}\\{dr.ProtoValues}\\{Mode}")
                    self._addArg(value)
                elif self.target == Enable:
                    if "value" not in self.kwargs or type(self.kwargs["value"]) != bool:
                        raise ValueError(
                            f"Value must be a boolean for GEQ enable command"
                        )
                    self._addArg(f"{geq}\\{dr.ProtoValues}\\{Enable}")
                    self._addArg(Enabled if value else Disabled)
                elif self.target == GeqBand:
                    if "bandNumber" not in self.kwargs:
                        raise ValueError(
                            f"Band number must be specified for GEQ band commands"
                        )
                    bandNumber = self.kwargs["bandNumber"]
                    if bandNumber not in Band.keys():
                        raise ValueError(f"Invalid band number {bandNumber}")

                    self._addArg(f"{geq}\\{dr.ProtoValues}\\{Band[bandNumber]}")
                    self._addArg(value)
