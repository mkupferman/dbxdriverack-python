#!/usr/bin/env python3

import dbxdriverack as dr
import dbxdriverack.pa2.peq as peq
import dbxdriverack.pa2.limiter as limiter
import dbxdriverack.pa2.outputdelay as odly

# Constants

## Output Band
BandLow = "Low"
BandMid = "Mid"
BandHigh = "High"
MuteEnabled = "On"
MuteDisabled = "Off"

## Generic Targets
MuteL = "MuteLeft"
MuteR = "MuteRight"

## Protocol
ProtoMutes = "\\\\Preset\\OutputGains"
MuteLowL = "LowLeftOutputMute"
MuteLowR = "LowRightOutputMute"
MuteMidL = "MidLeftOutputMute"
MuteMidR = "MidRightOutputMute"
MuteHighL = "HighLeftOutputMute"
MuteHighR = "HighRightOutputMute"


class PA2OutputBlock:
    """Represents an output block in a PA2 device (i.e. Low, Mid, or High)
    An output block is a combination of a PEQ, Limiter and Alignment Delay blocks.
    This also is designated to handle output muting.
    None of the methods directly affect a live device.

    Attributes
    ----------
    peq : PA2Peq
        The PEQ block for this output
    limiter : PA2Limiter
        The Limiter block for this output
    delay : PA2OutputDelay
        The Alignment Delay block for this output

    Constants
    ---------
    BandLow : str
        Low output band
    BandMid : str
        Mid output band
    BandHigh : str
        High output band
    MuteEnabled : str
        On state for the an output channel mute
    MuteDisabled : str
        Off state for the an output channel mute
    """

    def __init__(self) -> None:
        """
        Parameters
        ----------
        None

        Initialized with no bands set and no mute states.
        """

        pass

    def setPeq(self, peq: peq.PA2Peq) -> None:
        """Set the PEQ block for this output with a PA2Peq object

        Parameters
        ----------
        peq : peq.PA2Peq
            The PEQ block to set
        """

        self.peq = peq

    def setLimiter(self, limiter: limiter.PA2Limiter) -> None:
        """Set the Limiter block for this output with a PA2Limiter object

        Parameters
        ----------
        limiter : limiter.PA2Limiter
            The Limiter block to set
        """

        self.limiter = limiter

    def setDelay(self, delay: odly.PA2OutputDelay) -> None:
        """Set the Alignment Delay block for this output with a PA2OutputDelay object

        Parameters
        ----------
        delay : odly.PA2OutputDelay
            The Alignment Delay block to set
        """

        self.delay = delay

    def getPeq(self) -> peq.PA2Peq:
        """Get the PEQ block for this output

        Returns
        -------
        peq.PA2Peq
            The PEQ block for this output

        Raises
        ------
        ValueError
            PEQ not set
        """

        if hasattr(self, "peq"):
            return self.peq
        else:
            raise ValueError("PEQ not set")

    def getLimiter(self) -> limiter.PA2Limiter:
        """Get the Limiter block for this output

        Returns
        -------
        limiter.PA2Limiter
            The Limiter block for this output

        Raises
        ------
        ValueError
            Limiter not set
        """

        if hasattr(self, "limiter"):
            return self.limiter
        else:
            raise ValueError("Limiter not set")

    def getDelay(self) -> odly.PA2OutputDelay:
        """Get the Alignment Delay block for this output

        Returns
        -------
        odly.PA2OutputDelay
            The Alignment Delay block for this output

        Raises
        ------
        ValueError
            Output Delay not set
        """

        if hasattr(self, "delay"):
            return self.delay
        else:
            raise ValueError("Delay not set")


class CmdBuilder(dr.CmdBuilder):
    """Subclass of the CmdBuilder network protocol factory for DriveRack PA2."""

    def _generateCmd(self) -> None:
        if self.target in [MuteL, MuteR]:
            if "band" not in self.kwargs:
                raise ValueError("Band must be specified for mute commands")
            band = self.kwargs["band"]
            if band not in [BandLow, BandMid, BandHigh]:
                raise ValueError("Invalid band")
            if band == BandLow:
                muteTarget = MuteLowL if self.target == MuteL else MuteLowR
            elif band == BandMid:
                muteTarget = MuteMidL if self.target == MuteL else MuteMidR
            elif band == BandHigh:
                muteTarget = MuteHighL if self.target == MuteL else MuteHighR
            else:
                raise ValueError("Invalid band")

            self._addArg(f"{ProtoMutes}\\{dr.ProtoValues}\\{muteTarget}")

            if self.action == dr.ProtoSet:
                if "value" not in self.kwargs:
                    raise ValueError("Value must be specified for mute commands")
                value = self.kwargs["value"]
                if type(value) != bool:
                    raise ValueError("Value must be boolean for mute")

                self._addArg(MuteEnabled if value else MuteDisabled)
