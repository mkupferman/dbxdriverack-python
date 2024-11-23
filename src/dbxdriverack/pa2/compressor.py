#!/usr/bin/env python3

import dbxdriverack as dr

# Constants
Enabled = "On"
Disabled = "Off"
ThreshMin = -60
ThreshMax = 0
GainMin = -20
GainMax = 20
RatioMin = 1
RatioMax = 40
RatioBrickwall = -1.0
OverEasyMin = 0  # off
OverEasyMax = 10

## Compressor

## Protocol
Compressor = "\\\\Preset\\Compressor"
Enable = "Compressor"
Threshold = "Threshold"
Gain = "Gain"
Ratio = "Ratio"
OverEasy = "OverEasy"
Brickwall = "Inf"


class PA2Compressor:
    """Represents the compressor block settings in the DriveRack PA2.
    None of the methods directly affect a live device.

    Attributes
    ----------
    enabled : bool
        Whether the compressor is enabled
    threshold : float
        Threshold in dB
    gain : float
        Gain in dB
    ratio : float
        Ratio of compression (numerator only)
    overEasy : int
        OverEasy setting (0-10)

    Constants
    ---------
    Enabled : str
        On state for Compressor block
    Disabled : str
        Off state for Compressor block
    ThreshMin : int
        Minimum threshold in dB
    ThreshMax : int
        Maximum threshold in dB
    GainMin : int
        Minimum gain in dB
    GainMax : int
        Maximum gain in dB
    RatioMin : int
        Minimum ratio value
    RatioMax : int
        Maximum ratio value
    RatioBrickwall : float
        Infinity ratio value
    OverEasyMin : int
        Minimum OverEasy value
    OverEasyMax : int
        Maximum
    """

    def __init__(self, enabled: bool = True) -> None:
        """
        Parameters
        ----------
        enabled : bool, optional
            Enable or disable the compressor block, by default True
        """

        self.enabled: bool = enabled
        self.threshold: float = -20.0
        self.gain: float = 0.0
        self.ratio: float = 2.0
        self.overEasy: int = 0

    def setThreshold(self, threshold: float) -> None:
        """Set compressor threshold in dB.

        Parameters
        ----------
        threshold : float
            Threshold in dB

        Raises
        ------
        ValueError
            Threshold is out of range
        """

        if not (ThreshMin <= threshold <= ThreshMax):
            raise ValueError(
                f"Threshold must be in the range {ThreshMin} to {ThreshMax}"
            )
        self.threshold = threshold

    def setGain(self, gain: float) -> None:
        """Set compressor gain in dB.

        Parameters
        ----------
        gain : float
            Gain in dB

        Raises
        ------
        ValueError
            Gain is out of range
        """

        if not (GainMin <= gain <= GainMax):
            raise ValueError(f"Gain must be in the range {GainMin} to {GainMax}")
        self.gain = gain

    def setRatio(self, ratio: float) -> None:
        """Set the numerator of the ratio (denominator is always 1).

        Parameters
        ----------
        ratio : float
            Numerator of the ratio (<ratio>:1).
            Use compressor.RatioBrickwall for Infinity.

        Raises
        ------
        ValueError
            Ratio is out of range
        """

        if ratio == RatioBrickwall:
            self.ratio = RatioBrickwall
        elif not (RatioMin <= ratio <= RatioMax):
            raise ValueError(
                f"Ratio ({ratio}) not in the range {RatioMin} to {RatioMax}"
            )
        self.ratio = ratio

    def setOverEasy(self, overEasy: int) -> None:
        """Set the OverEasy setting (0-10), 0 is off.

        Parameters
        ----------
        overEasy : int
            OverEasy setting

        Raises
        ------
        ValueError
            OverEasy is out of range
        """

        if not (OverEasyMin <= overEasy <= OverEasyMax):
            raise ValueError(
                f"OverEasy must be in the range {OverEasyMin} to {OverEasyMax}"
            )
        self.overEasy = overEasy

    def enable(self) -> None:
        """Enable the compressor block"""
        self.enabled = True

    def disable(self) -> None:
        """Disable the compressor block"""
        self.enabled = False

    def getThreshold(self) -> float:
        """Get the compressor threshold in dB.

        Returns
        -------
        float
            Threshold in dB
        """

        return self.threshold

    def getGain(self) -> float:
        """Get the compressor gain in dB.

        Returns
        -------
        float
            Gain in dB
        """

        return self.gain

    def getRatio(self) -> float:
        """Get the compressor ratio (numerator only).
        Value of -1 (equal to compressor.RatioBrickwall) indicates Infinity.

        Returns
        -------
        float
            Ratio (numerator only)
        """

        return self.ratio

    def getOverEasy(self) -> int:
        """Get the OverEasy value (0-10), 0 is off.

        Returns
        -------
        int
            OverEasy value
        """

        return self.overEasy

    def isEnabled(self) -> bool:
        """Whether the compressor block is enabled.

        Returns
        -------
        bool
            True if enabled, False if disabled
        """

        return self.enabled

    def __str__(self) -> str:
        if self.ratio == RatioBrickwall:
            ratio = Brickwall
        else:
            ratio = str(self.ratio)
        return f"Compressor: {self.enabled}, Thresh {self.threshold}dB, Gain {self.gain}dB, {ratio}:1, OvEsy {self.overEasy}"


class CmdBuilder(dr.CmdBuilder):
    """Subclass of the CmdBuilder network protocol factory for DriveRack PA2."""

    def _generateCmd(self) -> None:
        if self.target in [Threshold, Gain, Ratio, OverEasy, Enable]:
            if self.command[0] == dr.ProtoGet:
                self._addArg(f"{Compressor}\\{dr.ProtoValues}\\{self.target}")
            elif self.command[0] == dr.ProtoSet:
                if "value" not in self.kwargs:
                    raise ValueError(
                        f"Value must be specified for compressor target {self.target}"
                    )
                value = self.kwargs["value"]

                if self.target == Enable:
                    if "value" not in self.kwargs or type(self.kwargs["value"]) != bool:
                        raise ValueError(
                            "Value must be a boolean for Compressor enable/disable"
                        )
                    self._addArg(f"{Compressor}\\{dr.ProtoValues}\\{Enable}")
                    self._addArg(Enabled if self.kwargs["value"] else Disabled)
                elif self.target == Threshold:
                    if not (ThreshMin <= value <= ThreshMax):
                        raise ValueError(
                            f"Threshold must be in the range {ThreshMin} to {ThreshMax}"
                        )
                    self._addArg(f"{Compressor}\\{dr.ProtoValues}\\{Threshold}")
                    self._addArg(value)
                elif self.target == Gain:
                    if not (GainMin <= value <= GainMax):
                        raise ValueError(
                            f"Gain must be in the range {GainMin} to {GainMax}"
                        )
                    self._addArg(f"{Compressor}\\{dr.ProtoValues}\\{Gain}")
                    self._addArg(value)
                elif self.target == Ratio:
                    if value != RatioBrickwall and not (RatioMin <= value <= RatioMax):
                        raise ValueError(
                            f"Ratio must be in the range {RatioMin} to {RatioMax} or {RatioBrickwall}"
                        )
                    self._addArg(f"{Compressor}\\{dr.ProtoValues}\\{Ratio}")
                    if value == RatioBrickwall:
                        self._addArg(f"{Brickwall}:1")
                    else:
                        self._addArg(f"{value:.1f}:1")
                elif self.target == OverEasy:
                    if not (OverEasyMin <= value <= OverEasyMax):
                        raise ValueError(
                            f"OverEasy must be in the range {OverEasyMin} to {OverEasyMax}"
                        )
                    self._addArg(f"{Compressor}\\{dr.ProtoValues}\\{OverEasy}")
                    self._addArg(value)
