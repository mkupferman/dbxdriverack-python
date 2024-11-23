#!/usr/bin/env python3


import dbxdriverack as dr

# Constants

## Auto EQ
Enabled = "On"
Disabled = "Off"
ModeFlat = "Flat"
ModeManual = "Manual"  # adjustments made imply Manual mode
ModeAuto = "AutoEQ"  # use wizard curve
Bell = "Bell"
LowShelf = "Low Shelf"
HighShelf = "High Shelf"
FiltMinCount = 1
FiltMaxCount = 8
BellMinQ = 0.1
BellMaxQ = 16.0
ShelfMinSlope = 3.0
ShelfMaxSlope = 15.0
MinGain = -20
MaxGain = 20

## Generic Targets
AutoEqType = "AutoEqType"
AutoEqFreq = "Frequency"
AutoEqQ = "Q"
AutoEqSlope = "Slope"
AutoEqGain = "Gain"

## Protocol
Enable = "ParametricEQ"
AutoEq = "\\\\Preset\\RoomEQ"
Mode = "Flatten"


class PA2AutoEqFilter:
    """Represents a single Auto EQ filter for the DriveRack PA2.

    Attributes
    ----------
    freq : float
        Filter frequency in Hz
    gain : float
        Filter gain in dB
    q : float
        Filter Q value. For shelf filters, this holds the slope instead.
    filtType : str
        Filter type. One of autoeq.Bell, autoeq.LowShelf, autoeq.HighShelf.

    Constants
    ---------
    Enabled : str
        On state for Auto EQ block
    Disabled : str
        Off state for Auto EQ block
    ModeFlat : str
        Flat mode for Auto EQ block
    ModeManual : str
        Manual mode for Auto EQ block
    ModeAuto : str
        Auto EQ mode for Auto EQ block
    Bell : str
        Bell filter type for Auto EQ filter
    LowShelf : str
        Low shelf filter type for Auto EQ filter
    HighShelf : str
        High shelf filter type for Auto EQ filter
    FiltMinCount : int
        Minimum number of filters in Auto EQ block
    FiltMaxCount : int
        Maximum number of filters in Auto EQ block
    BellMinQ : float
        Minimum Q value for Auto EQ bell filter
    BellMaxQ : float
        Maximum Q value for Auto EQ bell filter
    ShelfMinSlope : float
        Minimum slope for Auto EQ shelf filters
    ShelfMaxSlope : float
        Maximum slope for Auto EQ shelf filters
    MinGain : int
        Minimum gain in dB for an Auto EQ filter
    MaxGain : int
        Maximum gain in dB for an Auto EQ filter
    """

    def __init__(self, filtType: str, freq: float, gain: float, q: float) -> None:
        """
        Parameters
        ----------
        filtType : str
            One of autoeq.Bell, autoeq.LowShelf, autoeq.HighShelf
        freq : float
            Filter frequency in Hz
        gain : float
            Filter gain in dB
        q : float
            Filter Q value. For shelf filters, this holds the slope instead.

        Raises
        ------
        ValueError
            One of the parameters are out of range
        """

        if filtType not in [Bell, LowShelf, HighShelf]:
            raise ValueError(
                f"Filter type must be one of {Bell}, {LowShelf}, {HighShelf}"
            )

        if filtType == Bell and not (BellMinQ <= q <= BellMaxQ):
            raise ValueError(
                f"Q must be in the range {BellMinQ} to {BellMinQ} for Auto EQ bell type"
            )
        elif filtType in [LowShelf, HighShelf] and not (
            ShelfMinSlope <= q <= ShelfMaxSlope
        ):
            raise ValueError(
                f"Q must be in the range {ShelfMinSlope} to {ShelfMaxSlope} for Auto EQ shelf type"
            )

        if not (MinGain <= gain <= MaxGain):
            raise ValueError(
                f"Gain must be in the range {MinGain} to {MaxGain} for Auto EQ filter"
            )

        self.freq: float = freq
        self.gain: float = gain
        self.q: float = q
        self.filtType: str = filtType

    def __str__(self) -> str:
        return f"Filter Type: {self.filtType}, Freq: {self.freq:.2f}, Gain: {self.gain:.1f}, Q: {self.q:.1f}"


class PA2AutoEq:
    """Represents an Auto EQ (room EQ) block on a DriveRack PA2.
    This contains settings for the block as as well as the individual filters.
    None of the methods directly affect a live device.

    Attributes
    ----------
    filters : dict[int, PA2AutoEqFilter]
        Dictionary of Auto EQ filters. Key is the filter number (1-8)
    enabled : bool
        Whether the Auto EQ block is enabled
    """

    def __init__(self, enabled: bool = True) -> None:
        """
        Parameters
        ----------
        enabled : bool, optional
            Sets the initial enabled state of the Auto EQ block. Default is True.
        """

        self.filters: dict[int, PA2AutoEqFilter] = {}
        self.enabled: bool = enabled

    def addFilter(self, filter: PA2AutoEqFilter, filtNumber: int = -1) -> None:
        """Add a PA2AutoEqFilter to the Auto EQ block.

        Parameters
        ----------
        filter : PA2AutoEqFilter
            The filter to add.
        filtNumber : int, optional
            Index number to assign to the filter.
            If not specified, the next available index will be used.
        """

        if filtNumber == -1:
            filtNumber = len(self.filters) + 1

        if FiltMinCount <= filtNumber <= FiltMaxCount:
            self.filters[filtNumber] = filter

    def getFilter(self, filtNumber: int) -> PA2AutoEqFilter:
        """Get a filter from the Auto EQ block.

        Parameters
        ----------
        filtNumber : int
            The index number of the filter to retrieve.

        Returns
        -------
        PA2AutoEqFilter
            The PA2AutoEqFilter object with the specified index number.

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
        """Delete a filter from the Auto EQ block.

        Parameters
        ----------
        filtNumber : int
            The index number of the filter to remove.

        Raises
        ------
        ValueError
            No filter with the specified index number exists.
        """

        if filtNumber in self.filters:
            del self.filters[filtNumber]

    def enable(self) -> None:
        """Enable the Auto EQ block."""
        self.enabled = True

    def disable(self) -> None:
        """Disable the Auto EQ block."""
        self.enabled = False

    def _flatten(self) -> None:
        """Remove all filters from the Auto EQ block."""
        self.filters = {}

    def isEnabled(self) -> bool:
        """Get the enabled state of the Auto EQ block.

        Returns
        -------
        bool
            True if enabled, False if disabled
        """

        return self.enabled

    def __str__(self) -> str:
        return f"Enabled: {self.enabled}, #Filters: {len(self.filters)}"


class CmdBuilder(dr.CmdBuilder):
    """Subclass of the CmdBuilder network protocol factory for DriveRack PA2."""

    def _generateCmd(self) -> None:
        if self.target in [
            AutoEqType,
            AutoEqFreq,
            AutoEqQ,
            AutoEqSlope,
            AutoEqGain,
            Mode,
        ]:
            if "value" not in self.kwargs:
                raise ValueError(
                    f"Value must be specified for Auto EQ target {self.target}"
                )
            value = self.kwargs.get("value")

            if self.target == Mode:
                if value not in [ModeFlat, ModeManual, ModeAuto]:
                    raise ValueError("Invalid mode")
                self._addArg(f"{AutoEq}\\{dr.ProtoValues}\\{Mode}")
                self._addArg(value)
            elif self.target == Enable:
                if "value" not in self.kwargs or type(self.kwargs["value"]) != bool:
                    raise ValueError("Value must be boolean for Auto EQ enable/disable")
                self._addArg(f"{AutoEq}\\{dr.ProtoValues}\\{Enable}")
                self._addArg(Enabled if self.kwargs["value"] else Disabled)
            else:
                if "filtNumber" not in self.kwargs:
                    raise ValueError(
                        "Filter number must be specified for Auto EQ filter commands"
                    )
                filtNumber = self.kwargs["filtNumber"]

                if self.target == AutoEqType:
                    if value not in [Bell, LowShelf, HighShelf]:
                        raise ValueError(
                            f"Filter type must be one of {Bell}, {LowShelf}, {HighShelf}"
                        )
                    self._addArg(f"{AutoEq}\\{dr.ProtoValues}\\Band_{filtNumber}_Type")
                    self._addArg(value)
                elif self.target == AutoEqFreq:
                    self._addArg(
                        f"{AutoEq}\\{dr.ProtoValues}\\Band_{filtNumber}_Frequency"
                    )
                    self._addArg(f"{(value):.2f}")
                elif self.target == AutoEqQ:
                    self._addArg(f"{AutoEq}\\{dr.ProtoValues}\\Band_{filtNumber}_Q")
                    self._addArg(f"{(value):.1f}")
                elif self.target == AutoEqSlope:
                    self._addArg(f"{AutoEq}\\{dr.ProtoValues}\\Band_{filtNumber}_Slope")
                    self._addArg(f"{(value):.1f}")
                elif self.target == AutoEqGain:
                    self._addArg(f"{AutoEq}\\{dr.ProtoValues}\\Band_{filtNumber}_Gain")
                    self._addArg(f"{(value):.1f}")
