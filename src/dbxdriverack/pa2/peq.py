#!/usr/bin/env python3

import dbxdriverack as dr
import dbxdriverack.pa2.outputband as ob

# Constants

## PEQ
Enabled = "On"
Disabled = "Off"
Bell = "Bell"
LowShelf = "Low Shelf"
HighShelf = "High Shelf"
BellMinQ = 0.1
BellMaxQ = 16.0
ShelfMinSlope = 3.0
ShelfMaxSlope = 15.0
FiltMinCount = 1
FiltMaxCount = 8
MinGain = -20
MaxGain = 20
Flat = "Flat"
Restore = "Restore"

## Generic Targets
PeqType = "PeqType"
PeqFreq = "PeqFreq"
PeqQ = "PeqQ"
PeqSlope = "PeqSlope"
PeqGain = "PeqGain"

## Protocol
PeqFlat = "Flatten"
PeqEnable = "ParametricEQ"
PeqBandHigh = "\\\\Preset\\High Outputs PEQ"
PeqBandMid = "\\\\Preset\\Mid Outputs PEQ"
PeqBandLow = "\\\\Preset\\Low Outputs PEQ"


class PA2PeqFilter:
    """Represents a single PEQ filter for the DriveRack PA2.

    Attributes
    ----------
    freq : float
        Filter frequency in Hz
    gain : float
        Filter gain in dB
    q : float
        Filter Q value. For shelf filters, this holds the slope instead.
    filtType : str
        Filter type. One of peq.Bell, peq.LowShelf, peq.HighShelf.

    Constants
    ---------
    Enabled : str
        On state for PEQ block
    Disabled : str
        Off state for PEQ block
    Bell : str
        Bell filter type for PEQ filter
    LowShelf : str
        Low shelf filter type for PEQ filter
    HighShelf : str
        High shelf filter type for PEQ filter
    FiltMinCount : int
        Minimum number of filters in PEQ block
    FiltMaxCount : int
        Maximum number of filters in PEQ block
    BellMinQ : float
        Minimum Q value for Bell filter
    BellMaxQ : float
        Maximum Q value for Bell filter
    ShelfMinSlope : float
        Minimum slope value for shelf filters
    ShelfMaxSlope : float
        Maximum slope value for shelf filters
    MinGain : float
        Minimum gain value for PEQ filter
    MaxGain : float
        Maximum gain value for PEQ filter
    """

    def __init__(self, filtType: str, freq: float, gain: float, q: float) -> None:
        """
        Parameters
        ----------
        filtType : str
            Filter type. One of peq.Bell, peq.LowShelf, peq.HighShelf.
        freq : float
            Filter frequency in Hz
        gain : float
            Filter gain in dB
        q : float
            Filter Q value. For shelf filters, this holds the slope instead.

        Raises
        ------
        ValueError
            Invalid filter type or value
        """

        if filtType not in [Bell, LowShelf, HighShelf]:
            raise ValueError(f"filtType must be one of {Bell}, {LowShelf}, {HighShelf}")

        if filtType == Bell and not (BellMinQ <= q <= BellMaxQ):
            raise ValueError(
                f"Q must be in the range {BellMinQ} to {BellMinQ} for Bell type"
            )
        elif filtType in [LowShelf, HighShelf] and not (
            ShelfMinSlope <= q <= ShelfMaxSlope
        ):
            raise ValueError(
                f"Q must be in the range {ShelfMinSlope} to {ShelfMaxSlope} for Shelf type"
            )

        if not (MinGain <= gain <= MaxGain):
            raise ValueError(
                f"Gain must be in the range {MinGain} to {MaxGain} for PEQ filter"
            )

        self.freq = freq
        self.gain = gain
        self.q = q
        self.filtType = filtType

    def __str__(self) -> str:
        return f"Filter Type: {self.filtType}, Freq: {self.freq:.2f}, Gain: {self.gain:.1f}, Q: {self.q:.1f}"


class PA2Peq:
    """Represents a PEQ block for the DriveRack PA2.
    The PA2 can have up to 3 PEQ blocks, one for each output band (Low, Mid, High)
    and this object represents one of those PEQs, which can be applied to
    one of the available output bands of a PA2 device.
    None of the methods directly affect a live device.

    Attributes
    ----------
    filters : dict[int, PA2PeqFilter]
        Dictionary of PEQ filters. Key is the filter number (1-8)
    enabled : bool
        Whether the PEQ block is enabled

    Constants
    ---------
    Enabled : str
        On state for the PEQ block
    Disabled : str
        Off state for the PEQ block
    FiltMinCount : int
        Minimum number of filters in PEQ block
    FiltMaxCount : int
        Maximum number of filters in PEQ block
    """

    def __init__(self, enabled: bool = True) -> None:
        """
        Parameters
        ----------
        enabled : bool, optional
            Enabled state of the PEQ block. Default is True.
            Initialized with no filters.
        """

        self.filters: dict[int, PA2PeqFilter] = {}
        self.enabled = enabled

    def addFilter(self, filter: PA2PeqFilter, filtNumber: int = -1) -> None:
        """Add a PEQ filter to the PEQ block.

        Parameters
        ----------
        filter : PA2PeqFilter
            The filter to add
        filtNumber : int, optional
            Index number to assign to the filter.
            If not specified, the next available index will be used.
        """

        if filtNumber == -1:
            filtNumber = len(self.filters) + 1

        if FiltMinCount <= filtNumber <= FiltMaxCount:
            self.filters[filtNumber] = filter

    def enable(self) -> None:
        """Enable the PEQ block"""

        self.enabled = True

    def disable(self) -> None:
        """Disable the PEQ block"""

        self.enabled = False

    def flatten(self) -> None:
        """Remove all filters from the PEQ block"""

        self.filters = {}

    def getFilter(self, filtNumber: int) -> PA2PeqFilter:
        """Get a filter from the PEQ block.

        Parameters
        ----------
        filtNumber : int
            The index number of the filter to retrieve.

        Returns
        -------
        PA2PeqFilter
            The PA2PeqFilter object with the specified index number.

        Raises
        ------
        ValueError
            No filter with the specified index number exists.
        """

        if filtNumber in self.filters:
            return self.filters[filtNumber]
        else:
            raise ValueError(f"Filter {filtNumber} not found")

    def removeFilter(self, filtNumber: int) -> None:
        """Delete a filter from the PEQ block.

        Parameters
        ----------
        filtNumber : int
            The index number of the filter to remove.
        """

        if filtNumber in self.filters:
            del self.filters[filtNumber]

    def __str__(self) -> str:
        return f"Enabled: {self.enabled}, #Filters: {len(self.filters)}"


class CmdBuilder(dr.CmdBuilder):
    """Subclass of the CmdBuilder network protocol factory for DriveRack PA2."""

    def _generateCmd(self) -> None:
        if self.target in [
            PeqFlat,
            PeqType,
            PeqFreq,
            PeqQ,
            PeqSlope,
            PeqGain,
            PeqEnable,
        ]:
            if "band" not in self.kwargs:
                raise ValueError("Band must be specified for PEQ commands")
            band = self.kwargs["band"]
            if band not in [ob.BandLow, ob.BandMid, ob.BandHigh]:
                raise ValueError("Invalid band")
            if band == ob.BandLow:
                peqTarget = PeqBandLow
            elif band == ob.BandMid:
                peqTarget = PeqBandMid
            elif band == ob.BandHigh:
                peqTarget = PeqBandHigh
            else:
                raise ValueError("Invalid band")

            if self.target in [
                PeqType,
                PeqFreq,
                PeqQ,
                PeqSlope,
                PeqGain,
                PeqEnable,
                PeqFlat,
            ]:
                if "value" not in self.kwargs:
                    raise ValueError("Value must be specified for PEQ filter commands")
                value = self.kwargs["value"]

                if self.target == PeqFlat:
                    if value not in [Flat, Restore]:
                        raise ValueError(f"Invalid PEQ flat value: {value}")
                    self._addArg(f"{peqTarget}\\{dr.ProtoValues}\\{PeqFlat}")
                    self._addArg(value)
                elif self.target == PeqEnable:
                    if "value" not in self.kwargs or type(self.kwargs["value"]) != bool:
                        raise ValueError(
                            "Value must be specified and boolean for PEQ enable"
                        )
                    self._addArg(f"{peqTarget}\\{dr.ProtoValues}\\{PeqEnable}")
                    self._addArg(Enabled if self.kwargs["value"] else Disabled)

                else:
                    if "filtNumber" not in self.kwargs:
                        raise ValueError(
                            f"Filter number must be specified for PEQ filter commands (target: {self.target})"
                        )
                    filtNumber = self.kwargs["filtNumber"]

                    if self.target == PeqType:
                        if value not in [Bell, LowShelf, HighShelf]:
                            raise ValueError(f"Invalid PEQ filter type: {value}")
                        self._addArg(
                            f"{peqTarget}\\{dr.ProtoValues}\\Band_{filtNumber}_Type"
                        )
                        self._addArg(value)
                    elif self.target == PeqFreq:
                        self._addArg(
                            f"{peqTarget}\\{dr.ProtoValues}\\Band_{filtNumber}_Frequency"
                        )
                        self._addArg(f"{value:.2f}")
                    elif self.target == PeqQ:
                        self._addArg(
                            f"{peqTarget}\\{dr.ProtoValues}\\Band_{filtNumber}_Q"
                        )
                        self._addArg(f"{value:.1f}")
                    elif self.target == PeqSlope:
                        self._addArg(
                            f"{peqTarget}\\{dr.ProtoValues}\\Band_{filtNumber}_Slope"
                        )
                        self._addArg(f"{value:.1f}")
                    elif self.target == PeqGain:
                        self._addArg(
                            f"{peqTarget}\\{dr.ProtoValues}\\Band_{filtNumber}_Gain"
                        )
                        self._addArg(f"{value:.1f}")
            else:
                raise ValueError(f"Invalid target: {self.target}")
