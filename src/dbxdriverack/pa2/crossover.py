#!/usr/bin/env python3

import dbxdriverack as dr
import dbxdriverack.pa2.outputband as ob

# Constants

## Crossover
XoverLR12 = "LR 12"
XoverLR24 = "LR 24"
XoverLR36 = "LR 36"
XoverLR48 = "LR 48"
XoverBW6 = "BW 6"
XoverBW12 = "BW 12"
XoverBW18 = "BW 18"
XoverBW24 = "BW 24"
XoverBW30 = "BW 30"
XoverBW36 = "BW 36"
XoverBW42 = "BW 42"
XoverBW48 = "BW 48"
XoverFreqOut = -1
MinGain = -60
MaxGain = 20

## Generic Targets
XoverPolarity = "Polarity"
XoverHPType = "HPType"
XoverLPType = "LPType"
XoverHPFrequency = "HPFrequency"
XoverLPFrequency = "LPFrequency"
XoverGain = "Gain"

## Protocol
ProtoCrossover = "\\\\Preset\\Crossover"
XoverBandHigh = "Band_1"
XoverBandMid = "Band_2"
XoverBandLow = "Band_3"
XoverBandSub = "MonoSub"
XoverOut = "Out"


class PA2CrossoverBand:
    """Represents a band (i.e. High, Mid, Low) in the DriveRack PA2 crossover.
    This contains high-pass & low-pass filters as well as gain and polarity settings.
    None of the methods directly affect a live device.

    Attributes
    ----------
    polarity : str
        Polarity setting.
        One of dbxdriverack.PolarityNormal, dbxdriverack.PolarityInverted.
    hpfType : str
        High-pass filter type.
        One of the crossover filter constants.
    lpfType : str
        Low-pass filter type.
        One of the crossover filter constants.
    hpfFreq : float
        High-pass filter frequency in Hz.
    lpfFreq : float
        Low-pass filter frequency in Hz.
    gain : float
        Band gain in dB.

    Constants
    ---------
    MinGain : int
        Minimum band gain in dB.
    MaxGain : int
        Maximum band gain in dB.
    XoverFreqOut : int
        Special "Out" value for crossover frequency indicating max/min

    Crossover Frequency Constants
    -----------------------------
    XoverLR12 : str
        Linkwitz-Riley 12 dB/octave
    XoverLR24 : str
        Linkwitz-Riley 24 dB/octave
    XoverLR36 : str
        Linkwitz-Riley 36 dB/octave
    XoverLR48 : str
        Linkwitz-Riley 48 dB/octave
    XoverBW6 : str
        Butterworth 6 dB/octave
    XoverBW12 : str
        Butterworth 12 dB/octave
    XoverBW18 : str
        Butterworth 18 dB/octave
    XoverBW24 : str
        Butterworth 24 dB/octave
    XoverBW30 : str
        Butterworth 30 dB/octave
    XoverBW36 : str
        Butterworth 36 dB/octave
    XoverBW42 : str
        Butterworth 42 dB/octave
    XoverBW48 : str
        Butterworth 48 dB/octave
    """

    def __init__(self) -> None:
        """
        Parameters
        ----------
        None

        Begins with minimal default settings:
            Polarity: Normal
            HPF Type: 6 dB/octave Butterworth
            LPF Type: 6 dB/octave Butterworth
            HPF Freq: Out
            LPF Freq: Out
            Gain: 0
        """

        self.polarity: str = dr.PolarityNormal
        self.hpfType: str = XoverBW6
        self.lpfType: str = XoverBW6
        self.hpfFreq: float = XoverFreqOut
        self.lpfFreq: float = XoverFreqOut
        self.gain: float = 0.0

    def setGain(self, gain: float) -> None:
        """Set band gain in dB.

        Parameters
        ----------
        gain : float
            Gain in dB.

        Raises
        ------
        ValueError
            Gain is out of range.
        """

        if not (MinGain <= gain <= MaxGain):
            raise ValueError("Gain out of range")
        self.gain = gain

    def setPolarity(self, polarity: str) -> None:
        """Set band polarity.

        Parameters
        ----------
        polarity : str
            Polarity setting.
            One of dbxdriverack.PolarityNormal, dbxdriverack.PolarityInerted.

        Raises
        ------
        ValueError
            Invalid polarity choice.
        """

        if polarity not in [dr.PolarityNormal, dr.PolarityInverted]:
            raise ValueError("Polarity must be either Normal or Inverted")
        self.polarity = polarity

    def setHpfType(self, hpfType: str) -> None:
        """Set high-pass filter type.

        Parameters
        ----------
        hpfType : str
            High-pass filter type.
            One of the crossover filter constants.

        Raises
        ------
        ValueError
            Invalid HPF type.
        """

        if hpfType not in [
            XoverLR12,
            XoverLR24,
            XoverLR36,
            XoverLR48,
            XoverBW6,
            XoverBW12,
            XoverBW18,
            XoverBW24,
            XoverBW30,
            XoverBW36,
            XoverBW42,
            XoverBW48,
        ]:
            raise ValueError("Invalid HPF type")
        self.hpfType = hpfType

    def setLpfType(self, lpfType: str) -> None:
        """Set low-pass filter type.

        Parameters
        ----------
        lpfType : str
            Low-pass filter type.
            One of the crossover filter constants.

        Raises
        ------
        ValueError
            Invalid LPF type.
        """

        if lpfType not in [
            XoverLR12,
            XoverLR24,
            XoverLR36,
            XoverLR48,
            XoverBW6,
            XoverBW12,
            XoverBW18,
            XoverBW24,
            XoverBW30,
            XoverBW36,
            XoverBW42,
            XoverBW48,
        ]:
            raise ValueError("Invalid LPF type")
        self.lpfType = lpfType

    def setHpfFreq(self, hpfFreq: float) -> None:
        """Set high-pass filter frequency in Hz.

        Parameters
        ----------
        hpfFreq : float
            High-pass filter frequency in Hz.

        Raises
        ------
        ValueError
            Frequency is out of range.
        """

        if not (hpfFreq == XoverFreqOut or (16 <= hpfFreq <= 20000)):
            raise ValueError("HPF frequency out of range")
        self.hpfFreq = hpfFreq

    def setLpfFreq(self, lpfFreq: float) -> None:
        """Set low-pass filter frequency in Hz.

        Parameters
        ----------
        lpfFreq : float
            Low-pass filter frequency in Hz.

        Raises
        ------
        ValueError
            Frequency is out of range.
        """

        if not (lpfFreq == XoverFreqOut or (16 <= lpfFreq <= 20000)):
            raise ValueError("LPF frequency out of range")
        self.lpfFreq = lpfFreq

    def getGain(self) -> float:
        """Get band gain in dB.

        Returns
        -------
        float
            Gain in dB.
        """

        return self.gain

    def getPolarity(self) -> str:
        """Get band polarity.

        Returns
        -------
        str
            Band polarity.
            One of dbxdriverack.PolarityNormal, dbxdriverack.PolarityInerted.
        """

        return self.polarity

    def getHpfType(self) -> str:
        """Get high-pass filter type.

        Returns
        -------
        str
            High-pass filter type.
            One of the crossover filter constants.
        """

        return self.hpfType

    def getLpfType(self) -> str:
        """Get low-pass filter type.

        Returns
        -------
        str
            Low-pass filter type.
            One of the crossover filter constants.
        """

        return self.lpfType

    def getHpfFreq(self) -> float:
        """Get high-pass filter frequency in Hz.

        Returns
        -------
        float
            High-pass filter frequency in Hz.
        """

        return self.hpfFreq

    def getLpfFreq(self) -> float:
        """Get low-pass filter frequency in Hz.

        Returns
        -------
        float
            Low-pass filter frequency in Hz.
        """

        return self.lpfFreq

    def __str__(self) -> str:
        if self.hpfFreq == XoverFreqOut:
            hpfFreq = XoverOut
        else:
            hpfFreq = str(self.hpfFreq)

        if self.lpfFreq == XoverFreqOut:
            lpfFreq = XoverOut
        else:
            lpfFreq = str(self.lpfFreq)

        return (
            f"Polarity: {self.polarity}, HPF Type: {self.hpfType}, HPF Freq: {hpfFreq}, "
            f"LPF Type: {self.lpfType}, LPF Freq: {lpfFreq}, Gain: {self.gain}"
        )


class PA2Crossover:
    """Represents the crossover block on a DriveRack PA2.
    This contains up to three bands (Low, Mid, High) of type PA2CrossoverBand.
    Whether or not these bands can be applied depends on the wizard configuration of the PA2.
    None of the methods directly affect a live device.

    Attributes
    ----------
    bandLow : PA2CrossoverBand
        Low band settings.
    bandMid : PA2CrossoverBand
        Mid band settings.
    bandHigh : PA2CrossoverBand
        High band settings.
    """

    def __init__(self) -> None:
        """Use setLow(), setMid(), and setHigh() to set applicable bands."""

        pass

    def setLow(self, band: PA2CrossoverBand) -> None:
        """Set the low band settings.

        Parameters
        ----------
        band : PA2CrossoverBand
            Low band object
        """

        self.bandLow = band

    def setMid(self, band: PA2CrossoverBand) -> None:
        """Set the mid band settings.

        Parameters
        ----------
        band : PA2CrossoverBand
            Mid band object
        """

        self.bandMid = band

    def setHigh(self, band: PA2CrossoverBand) -> None:
        """Set the high band settings.

        Parameters
        ----------
        band : PA2CrossoverBand
            High band object
        """

        self.bandHigh = band

    def getLow(self) -> PA2CrossoverBand:
        """Get the low band settings.

        Returns
        -------
        _type_
            Low band object

        Raises
        ------
        ValueError
            Low band not set
        """

        try:
            self.bandLow
        except AttributeError:
            raise ValueError("Low band not set")

        return self.bandLow

    def getMid(self) -> PA2CrossoverBand:
        """Get the mid band settings.

        Returns
        -------
        _type_
            Mid band object

        Raises
        ------
        ValueError
            Mid band not set
        """

        try:
            self.bandMid
        except AttributeError:
            raise ValueError("Mid band not set")

        return self.bandMid

    def getHigh(self) -> PA2CrossoverBand:
        """Get the high band settings.

        Returns
        -------
        _type_
            High band object

        Raises
        ------
        ValueError
            High band not set
        """

        try:
            self.bandHigh
        except AttributeError:
            raise ValueError("High band not set")

        return self.bandHigh

    def __str__(self) -> str:
        output = ""
        try:
            self.bandHigh
        except AttributeError:
            pass
        else:
            output += f"High: {self.bandHigh}\n"

        try:
            self.bandMid
        except AttributeError:
            pass
        else:
            output += f"Mid: {self.bandMid}\n"

        try:
            self.bandLow
        except AttributeError:
            pass
        else:
            output += f"Low: {self.bandLow}\n"

        return output


class CmdBuilder(dr.CmdBuilder):
    """Subclass of the CmdBuilder network protocol factory for DriveRack PA2."""

    def _generateCmd(self) -> None:
        if self.target in [
            XoverPolarity,
            XoverHPType,
            XoverLPType,
            XoverHPFrequency,
            XoverLPFrequency,
            XoverGain,
        ]:
            if "lowMono" not in self.kwargs:
                raise ValueError("lowMono must be passed for crossover commands")
            if "band" not in self.kwargs:
                raise ValueError("Band must be specified for crossover commands")
            band = self.kwargs["band"]
            if band not in [ob.BandLow, ob.BandMid, ob.BandHigh]:
                raise ValueError("Invalid band")
            if band == ob.BandLow:
                if self.kwargs["lowMono"]:
                    xoverBand = XoverBandSub
                else:
                    xoverBand = XoverBandLow
            elif band == ob.BandMid:
                xoverBand = XoverBandMid
            elif band == ob.BandHigh:
                xoverBand = XoverBandHigh
            else:
                raise ValueError("Invalid band")
            if "value" not in self.kwargs:
                raise ValueError("Value must be specified for crossover commands")
            value = self.kwargs["value"]
            if self.target in [XoverHPFrequency, XoverLPFrequency, XoverGain]:
                if value == XoverFreqOut:
                    self._percent(True)
                    if self.target == XoverHPFrequency:
                        value = 0
                    elif self.target == XoverLPFrequency:
                        value = 100
                else:
                    value = f"{value:.2f}"

            self._addArg(
                f"{ProtoCrossover}\\{dr.ProtoValues}\\{xoverBand}_{self.target}{self.pct}"
            )
            if value == XoverFreqOut:
                self._addArg(XoverOut)
            else:
                self._addArg(str(value))
