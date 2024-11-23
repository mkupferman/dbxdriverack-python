#!/usr/bin/env python3

import dbxdriverack as dr

# Constants

## Advanced Feedback Suppression
Enabled = "On"
Disabled = "Off"
ModeLive = "Live"
ModeFixed = "Fixed"
TypeSpeech = "Speech"
TypeMusic = "Music"
TypeSpeechMusic = "Speech Music"
Clear = "1"
LiftMin = 5
LiftMax = 3600
FiltMin = 0
FiltMax = 12

## Protocol
AFS = "\\\\Preset\\Afs"
Enable = "AFS"
LiftTime = "LiftTime"
ClearLive = "ClearLive"
ClearAll = "ClearAll"
LiveLift = "LiveLiftEnable"
Filter = "FilterMode"
Content = "ContentMode"
FixedFilters = "MaxFixedFilters"


class PA2Feedback:
    """Represents the Advanced Feedback Suppression block of a DriveRack PA2.
    None of the methods directly affect a live device.

    Attributes
    ----------
    enabled : bool
        Whether the feedback suppression is enabled
    liftTime : float
        The lift time in seconds
    fixedFilters : int
        The number of fixed filters
    mode : str
        The operating mode. One of feedback.ModeLive, feedback.ModeFixed.
    type : str
        The program material type.
        One of feedback.TypeSpeech, feedback.TypeMusic, feedback.TypeSpeechMusic.

    Constants
    ---------
    Enabled : str
        On state for AFS block
    Disabled : str
        Off state for AFS block
    ModeLive : str
        Live mode for AFS block
    ModeFixed : str
        Fixed mode for AFS block
    TypeSpeech : str
        Speech content type for AFS block
    TypeMusic : str
        Music content type for AFS block
    TypeSpeechMusic : str
        Speech and music content type for AFS block
    LiftMin : int
        Minimum lift time in seconds
    LiftMax : int
        Maximum lift time in seconds
    FiltMin : int
        Minimum number of filters
    FiltMax : int
        Maximum number of filters
    """

    def __init__(self, enabled: bool = True) -> None:
        """
        Parameters
        ----------
        enabled : bool, optional
            _description_, by default True

        Other than enabling or disabling the the AFS block,
        default values are set to the following:
            Lift Time: 0s
            Fixed Filters: 0
            Mode: Live
            Type: Speech/Music
        """

        self.enabled: bool = enabled
        self.liftTime: float = 0.0
        self.fixedFilters: int = 0
        self.mode: str = ModeLive
        self.type: str = TypeSpeechMusic

    def setFixedFilters(self, filters: int) -> None:
        """Set the number of fixed filters.
        The remaining filters are live filters.

        Parameters
        ----------
        filters : int
            Number of fixed filters

        Raises
        ------
        ValueError
            Number of fixed filters is out of range (0-12)
        """

        if not (FiltMin <= filters <= FiltMax):
            raise ValueError(
                f"Fixed filters must be in the range {FiltMin} to {FiltMax}"
            )
        self.fixedFilters = filters

    def setLiftTime(self, time: float) -> None:
        """Set the lift time in seconds.

        Parameters
        ----------
        time : float
            The lift time in seconds

        Raises
        ------
        ValueError
            Lift time is out of range (5-3600)
        """

        if not (LiftMin <= time <= LiftMax):
            raise ValueError(f"Lift time must be in the range {LiftMin} to {LiftMax}")
        self.liftTime = time

    def enable(self) -> None:
        """Enable the feedback suppression block."""

        self.enabled = True

    def disable(self) -> None:
        """Disable the feedback suppression block."""

        self.enabled = False

    def setMode(self, mode: str) -> None:
        """Set the operating mode of the feedback suppression block.

        Parameters
        ----------
        mode : str
            Mode of operation.
            One of feedback.ModeLive, feedback.ModeFixed.

        Raises
        ------
        ValueError
            Invalid mode selection
        """

        if mode not in [ModeLive, ModeFixed]:
            raise ValueError("Invalid mode")
        self.mode = mode

    def setType(self, type: str) -> None:
        """Set the program material type.

        Parameters
        ----------
        type : str
            Material type.
            One of feedback.TypeSpeech, feedback.TypeMusic, feedback.TypeSpeechMusic.

        Raises
        ------
        ValueError
            Invalid type selection
        """

        if type not in [TypeSpeech, TypeMusic, TypeSpeechMusic]:
            raise ValueError("Invalid type")
        self.type = type

    def getFixedFilters(self) -> int:
        """Get the number of fixed filters.

        Returns
        -------
        int
            Number of fixed filters
        """

        return self.fixedFilters

    def getLiftTime(self) -> float:
        """Get the lift time in seconds.

        Returns
        -------
        float
            Lift time in seconds
        """

        return self.liftTime

    def isEnabled(self) -> bool:
        """Get the enabled state of the feedback suppression block.

        Returns
        -------
        bool
            True if enabled, False if disabled
        """

        return self.enabled

    def __str__(self) -> str:
        return f"Enabled: {self.enabled}, Mode: {self.mode}, Type: {self.type}, Lift Time: {self.liftTime}, Fixed Filters: {self.fixedFilters}"


class CmdBuilder(dr.CmdBuilder):
    """Subclass of the CmdBuilder network protocol factory for DriveRack PA2."""

    def _generateCmd(self) -> None:
        if self.command[0] == dr.ProtoGet:
            if self.target in [Enable, LiftTime, FixedFilters, Filter, Content]:
                self._addArg(f"{AFS}\\{dr.ProtoValues}\\{self.target}")
        elif self.command[0] == dr.ProtoSet:
            if self.target in [Enable, LiftTime, FixedFilters, Filter, Content]:
                if "value" not in self.kwargs:
                    raise ValueError(
                        f"Value must be specified for AFS target {self.target}"
                    )
                value = self.kwargs["value"]

                if self.target == Content:
                    if value not in [TypeSpeech, TypeMusic, TypeSpeechMusic]:
                        raise ValueError("Invalid content type")
                    self._addArg(f"{AFS}\\{dr.ProtoValues}\\{Content}")
                    self._addArg(value)
                elif self.target == Filter:
                    if value not in [ModeLive, ModeFixed]:
                        raise ValueError("Invalid filter mode")
                    self._addArg(f"{AFS}\\{dr.ProtoValues}\\{Filter}")
                    self._addArg(value)
                elif self.target == Enable:
                    if "value" not in self.kwargs or type(self.kwargs["value"]) != bool:
                        raise ValueError("Value must be boolean for AFS enable/disable")
                    self._addArg(f"{AFS}\\{dr.ProtoValues}\\{Enable}")
                    self._addArg(Enabled if self.kwargs["value"] else Disabled)
                elif self.target == LiftTime:
                    if not (LiftMin <= value <= LiftMax):
                        raise ValueError(
                            f"Lift time must be in the range {LiftMin} to {LiftMax}"
                        )
                    self._addArg(f"{AFS}\\{dr.ProtoValues}\\{LiftTime}")
                    self._addArg(f"{int(value)}")
                elif self.target == FixedFilters:
                    if not (FiltMin <= value <= FiltMax):
                        raise ValueError(
                            f"Fixed filters must be in the range {FiltMin} to {FiltMax}"
                        )
                    self._addArg(f"{AFS}\\{dr.ProtoValues}\\{FixedFilters}")
                    self._addArg(f"{int(value)}")
            elif self.target in [LiveLift, ClearLive, ClearAll]:
                self._addArg(f"{AFS}\\{dr.ProtoValues}\\{self.target}")
                self._addArg(Enabled)
