#!/usr/bin/env python3

"""Provides functions and state tracking for discoveriung, connecting to,
reading, and controlling aspects of a dbx DriveRack PA2 device.
"""

import threading
import queue
from datetime import datetime
import socket
import time
import re
import shlex
from typing import Type, Optional, Self, Any
from collections.abc import Callable, Mapping, ItemsView
from types import TracebackType

from tssplit import tssplit  # type: ignore

import dbxdriverack as dr
import dbxdriverack.pa2.crossover as xo
import dbxdriverack.pa2.outputband as ob
import dbxdriverack.pa2.peq as peq
import dbxdriverack.pa2.outputdelay as odly
import dbxdriverack.pa2.limiter as lim
import dbxdriverack.pa2.autoeq as aeq
import dbxdriverack.pa2.geq as geq
import dbxdriverack.pa2.feedback as afs
import dbxdriverack.pa2.subharmonic as sub
import dbxdriverack.pa2.compressor as comp
import dbxdriverack.pa2.indelay as idly
import dbxdriverack.pa2.rta as rta
import dbxdriverack.pa2.generator as gen

# Constants

## DriveRack PA2
DeviceModel = "dbxDriveRackPA2"
DeviceVersions = ["1.2.0.1"]

## Protocol
ProtoModel = "\\\\Node\\AT\\Class_Name"
ProtoName = "\\\\Node\\AT\\Instance_Name"
ProtoVersion = "\\\\Node\\AT\\Software_Version"
Preset = "\\\\Preset"


class PA2Device:
    """Represents a DriveRack PA2 device's model, name, and other characteristics.

    Attributes
    ----------
    addr : str
        The IP address or hostname of the device
    name : str
        The name of the device
    model : str
        The model of the device
    version : str
        The software version of the device
    """

    def __init__(self, addr: str):
        """
        Parameters
        ----------
        addr : str
            Address (IP/hostname) of the device
        """

        self.addr: str = addr
        self.name: str = "unknown"
        self.model: str = "unknown"
        self.version: str = "unknown"

    def __str__(self) -> str:
        return f"{self.model} (v{self.version}): {self.addr} ({self.name})"

    def __repr__(self) -> str:
        return self.__str__()


class PA2:
    """Represents a dbx DriveRack PA2 device and provides methods for
    discovering, connecting to, and controlling the device.
    """

    listRegex = re.compile(r"^\s*([^:\s]+)\s*:\s*(.*)\s*$")

    def __init__(self, debug: bool = False) -> None:
        """
        Parameters
        ----------
        debug : bool, optional
            When True, timestamped debug messages are printed to stdout upon exit. Default: False
        """

        self.debug = debug

        self.errors: queue.Queue[str] = queue.Queue()

        self.networkThread = None
        self.inputQueueThread = None
        self.outputQueueThread = None

        self._clearHandshake()

        self.inputQueue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.outputQueue: queue.Queue[tuple[tuple[str, int], str]] = queue.Queue()
        self.disconnectLock: bool = False

        self.threads: queue.Queue[threading.Thread] = queue.Queue()

        # list response tracking
        try:
            del self.listLock
        except:
            pass
        self.listData: dict[str, str] = {}

        # individual blocking target commands
        self.blockList: dict[str, list[str]] = {}
        self.blockRetried = False
        self.blockError = False

        self.discoveredDevices: dict[str, PA2Device] = {}

        self.version: str = "unknown"
        self.model: str = "unknown"
        self.name: str = "unknown"

        self.geqs: dict[str, geq.PA2Geq] = {
            "L": geq.PA2Geq(),
            "R": geq.PA2Geq(),
            "St": geq.PA2Geq(),
        }
        self.stereoGeq = True

        self.outHigh = ob.PA2OutputBlock()
        self.outMid = ob.PA2OutputBlock()
        self.outLow = ob.PA2OutputBlock()
        self.numBands = 0
        self.lowMono = False

    def _dprint(self, e: str) -> None:
        """Queue a debug message"""
        tsError = f"{datetime.now()}: {e}"
        self.errors.put(tsError)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        type: Optional[Type[BaseException]],
        value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self._dprint("Exit called")
        self._disconnect()

        if self.debug:
            errors_list: list[str] = []
            while not self.errors.empty():
                errors_list.append(self.errors.get())
            for error in sorted(errors_list):
                print(error)

    def __del__(self) -> None:
        self._dprint("Destructor called")
        self._disconnect()

    def _hasSocket(self) -> bool:
        try:
            self.socket
        except AttributeError:
            return False

        return True

    def _clearHandshake(self) -> None:
        self.connected = False
        self.handshake = False
        self.authenticated = False
        self.validated = False
        try:
            del self.connectedAt
        except:
            pass

    def _queuesEmpty(self) -> bool:
        self._dprint(
            f"Queue check: {self.inputQueue.empty()} {self.outputQueue.empty()}"
        )
        return self.inputQueue.empty() and self.outputQueue.empty()

    def _drainThreads(self) -> None:
        self._dprint("Draining threads")
        while not self.threads.empty():
            thread = self.threads.get()
            self._dprint(f"Joining thread {thread}")
            if thread and thread.is_alive():
                try:
                    thread.join()
                except:
                    pass

    def _disconnect(self) -> None:
        self._dprint("Disconnecting")
        if self.disconnectLock:
            self._dprint("Disconnect lock is active")
            return

        self.disconnectLock = True

        if self.connected and self._queuesEmpty():
            self._dprint("Clean disconnect, no queues")
            if self._hasSocket():
                self._dprint("Shutting down socket")
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                self.socket.close()
                del self.socket
        else:
            # wait self.timeout seconds for the queues to empty
            timestamp = datetime.now()

            while (
                not self._queuesEmpty()
                and (datetime.now() - timestamp).total_seconds() < self.timeout
            ):
                self._dprint("Waiting for queues to empty")
                time.sleep(1)

            if not self._queuesEmpty() and self._hasSocket():
                self._dprint("Forced disconnect")
                self._dprint("Shutting down socket in forced disconnect")
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                    self.socket.close()
                except:
                    pass
                del self.socket

        self._clearHandshake()
        self.connected = False
        self._drainThreads()
        self.disconnectLock = False
        self._dprint("Disconnected routine complete")

    def _openConnection(self) -> bool:
        if self._hasSocket():
            self._dprint("Socket already open, disconnecting")
            self._disconnect()
        self.socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # pad the timeout by 10% to prevent firing an exception before out timer
        self.socket.settimeout(self.timeout * 1.1)
        try:
            self.socket.connect((self.host, self.port))
            self.inputSocketFile = self.socket.makefile("r")
        except socket.timeout:
            self._disconnect()
            raise ConnectionError(f"Connection to {self.host}:{self.port} timed out")
        self.connected = True
        self.connectedAt: datetime = datetime.now()
        return self.connected

    def _discoveryTimeout(self) -> None:
        while self.connected:
            threading.Event().wait(1)
            if (
                self._hasConnectedTime()
                and (datetime.now() - self.connectedAt).total_seconds() > self.timeout
            ):
                self._dprint("Discovery timed out")
                self._disconnect()

    def _authenticate(self) -> None:
        while self.connected and not (
            self.handshake and self.authenticated and self.validated
        ):
            threading.Event().wait(1)
            if (
                self._hasConnectedTime()
                and (datetime.now() - self.connectedAt).total_seconds() > self.timeout
            ):
                self._disconnect()
                raise ConnectionError("Handshake timed out")

            if self.authenticated and not self.validated:
                if self.model == DeviceModel and self.version in DeviceVersions:
                    self.validated = True

    def _readNetwork(self, mode: str = "tcp") -> None:
        while self.connected:
            data = ""
            if mode == "tcp":
                try:
                    data = self.inputSocketFile.readline()
                except:
                    self._dprint("Socket read error")
                    break
                else:
                    if data == "":
                        self._dprint("Socket read error/EOF")
                        break
                    self.inputQueue.put(("NA", data))
            elif mode == "udp":
                addr = ""
                try:
                    bdata, addr = self.socket.recvfrom(2048)
                    data = bdata.decode("utf-8")
                except:
                    self._dprint("Socket read error")
                    break
                else:
                    if data == "":
                        self._dprint("Socket read error/EOF")
                        break
                    for line in data.splitlines():
                        self.inputQueue.put((addr, line))

            if self.debug:
                self._dprint(f"< {data}")

    def _blockingQuery(self) -> None:
        """Wait (block) until values for all targets in question are received.
        _processCommand() will be responsible for looking for the responses
        and marking them as received.
        """

        try:
            self.blockStarted
        except AttributeError:
            pass
        else:
            raise ValueError("Blocking query already in progress")

        self.blockStarted: datetime = datetime.now()
        self._dprint(f"Blocking query started at {self.blockStarted}")
        while not self.blockError and (self.blockingForList or len(self.blockList) > 0):
            pass

        if self.blockError:
            if self.blockingForList:
                raise TimeoutError(
                    "Blocking query timed out waiting for list command to return"
                )
            else:
                raise TimeoutError(
                    f"Blocking query timed out waiting for {self.blockList.keys()}"
                )

        self._dprint(f"Blocking query completed at {datetime.now()}")
        try:
            del self.blockStarted
        except:
            pass
        self.blockRetried = False

    def _hasBlockStartTime(self) -> bool:
        try:
            self.blockStarted
        except AttributeError:
            return False

        return True

    def _processInputQueue(self, mode: str = "tcp") -> None:
        # Use a cache to avoid self.blockStarted changing
        # between existence check and subtraction by another thread
        if self._hasBlockStartTime():
            blockStartCache = self.blockStarted

        while self.connected or not self.connected and not self.inputQueue.empty():
            if not self.inputQueue.empty():
                message = self.inputQueue.get()
                self._parseMessage(message, mode=mode)

            # Check for a timeout on blocked commands.
            # If timeout and max retries are not reached, requeue the command
            if self._hasBlockStartTime():
                blockStartCache = self.blockStarted
                if (datetime.now() - blockStartCache).total_seconds() > self.timeout:
                    if not self.blockRetried:
                        self._dprint("Blocking query timed out, not yet retried")
                        for target, command in self.blockList.items():
                            self._dprint(f"Retrying {target}")
                            self._queueCommand(command, block=False)

                        self.blockStarted = datetime.now()
                        self.blockRetried = True
                    else:
                        self._dprint(
                            f"Blocking query timed out, retries exhausted. Remaining targets: {self.blockList.keys()}"
                        )

                        self.blockError = True

        self._dprint("Exiting input queue loop")

    def _queueCommand(self, command: list[str], block: bool = False) -> None:
        """Queue a command to be sent to the device.
        If block is True, assume the 2nd argument is the target and
        put the command into a list to be watched for by _processCommand().
        """

        # TODO: only output commands other than validation/authentication until validated
        # use an override flag in the init of the class to allow for unsupported models/verions
        commandString = shlex.join(command)
        self.outputQueue.put((("null", 0), commandString))

        if block:
            self._dprint(f"Requested block for command: {commandString}")
            if command[0] == dr.ProtoList:
                self.blockingForList = True
                self._dprint(f"Blocking for list {command[1]}")
            else:
                if len(command) < 2:
                    raise ValueError(
                        f"Block command requires at least 2 arguments. Received: {command}"
                    )
                target = command[1]
                self.blockList[target] = command
                self._dprint(f"Blocking for {target}")

    def _processOutputQueue(self, mode: str = "tcp") -> None:
        while self.connected or not self.connected and not self.outputQueue.empty():
            if not self.outputQueue.empty():
                messageContainer = self.outputQueue.get()
                if mode == "udp":
                    dest, message = messageContainer
                    self.socket.sendto(f"{message}\n".encode("utf-8"), dest)
                else:
                    message = messageContainer[1]
                    self.socket.sendall(f"{message}\n".encode("utf-8"))
                if self.debug:
                    self._dprint(f"> {message}")
        self._dprint("Exiting output queue loop")

    def _parseMessage(
        self, messageContainer: tuple[str, str], mode: str = "tcp"
    ) -> None:
        if mode == "udp":
            # discovery mode. extract the tuple (addr, message)
            addr, message = messageContainer
            addr = addr[0]
            message = message.strip()
            command: Any = tssplit(message, delimiter=" ")
            argc = len(command)
            if argc == 3 and command[0] in (dr.ProtoGet, dr.ProtoSubResp):
                if addr not in self.discoveredDevices:
                    self.discoveredDevices[addr] = PA2Device(addr)
                if command[1] == ProtoModel:
                    self.discoveredDevices[addr].model = command[2]
                elif command[1] == ProtoName:
                    self.discoveredDevices[addr].name = command[2]
                elif command[1] == ProtoVersion:
                    self.discoveredDevices[addr].version = command[2]

        elif mode == "tcp":
            message = messageContainer[1]
            message = message.strip()

            try:
                self.listLock
            except AttributeError:
                if not self.handshake:
                    if message == dr.ProtoHello:
                        self.handshake = True
                        self._queueCommand(
                            [dr.ProtoConnect, dr.AuthAdmin, self.password]
                        )
                else:
                    if not self.authenticated:
                        if message.startswith(dr.ProtoConnectAck):
                            # authentication successful
                            self._queueCommand([dr.ProtoGet, ProtoModel])
                            self._queueCommand([dr.ProtoGet, ProtoVersion])
                            self._queueCommand([dr.ProtoGet, ProtoName])
                            self._queueCommand(
                                [
                                    dr.ProtoList,
                                    f"{xo.ProtoCrossover}\\{dr.ProtoAttr}",
                                ]
                            )
                            self.authenticated = True
                        elif message.startswith(dr.ProtoConnectFail):
                            self._disconnect()
                            raise ConnectionError("Authentication failed")
                    else:
                        # authenticated
                        self._processCommand(message)
            else:
                if message == self.listLock:
                    self._processLatestList()
                    del self.listLock
                else:
                    # process "ls" list item
                    match = PA2.listRegex.match(message)
                    if match:
                        key, value = match.groups()
                        self.listData[key] = value

    def _processLatestList(self) -> None:
        """Call this method when the end of a list ("endls")
        is reached to process the list data.
        """

        # Crossover state
        if self.listTarget == f"{xo.ProtoCrossover}\\{dr.ProtoAttr}":
            if "NumBands" in self.listData and "MonoSub" in self.listData:
                self.numBands = int(self.listData["NumBands"])
                self.lowMono = int(self.listData["MonoSub"]) == 1
        elif self.listTarget == f"{Preset}":
            if "LeftGEQ" in self.listData:
                self.stereoGeq = False
        elif self.listTarget == f"{aeq.AutoEq}\\{dr.ProtoValues}":
            try:
                self.autoEq
            except AttributeError:
                self.autoEq: aeq.PA2AutoEq = aeq.PA2AutoEq()

            if "ParametricEQ" in self.listData:
                if self.listData["ParametricEQ"] == aeq.Enabled:
                    self.autoEq.enable()
                else:
                    self.autoEq.disable()
            for filtNumber in range(aeq.FiltMinCount, aeq.FiltMaxCount + 1):
                if f"Band_{filtNumber}_Type" in self.listData:
                    bandType = self.listData[f"Band_{filtNumber}_Type"]
                    freq = dr.freq2Hz(self.listData[f"Band_{filtNumber}_Frequency"])
                    q = float(self.listData[f"Band_{filtNumber}_Q"])
                    slope = float(self.listData[f"Band_{filtNumber}_Slope"])
                    gain = dr.dB2float(self.listData[f"Band_{filtNumber}_Gain"])
                    if bandType == aeq.Bell:
                        aeqBand = aeq.PA2AutoEqFilter(bandType, freq, gain, q)
                    elif bandType in (aeq.LowShelf, aeq.HighShelf):
                        aeqBand = aeq.PA2AutoEqFilter(bandType, freq, gain, slope)
                    else:
                        raise ValueError(f"Invalid band type: {bandType}")
                    self.autoEq.addFilter(aeqBand, filtNumber=filtNumber)
        elif self.listTarget.startswith(f"{xo.ProtoCrossover}\\{dr.ProtoValues}"):
            try:
                self.crossover
            except AttributeError:
                self.crossover: xo.PA2Crossover = xo.PA2Crossover()

            for band in [ob.BandHigh, ob.BandMid, ob.BandLow]:
                if band == ob.BandHigh:
                    bandName = xo.XoverBandHigh
                elif band == ob.BandMid:
                    if not self.hasMids():
                        continue
                    bandName = xo.XoverBandMid
                elif band == ob.BandLow:
                    if not self.hasSubs():
                        continue
                    if self.lowMono:
                        bandName = xo.XoverBandSub
                    else:
                        bandName = xo.XoverBandLow
                else:
                    raise ValueError(f"Invalid band: {band}")

                xoverBand = xo.PA2CrossoverBand()
                xoverBand.setHpfType(self.listData[f"{bandName}_HPType"])
                if self.listData[f"{bandName}_HPFrequency"] == xo.XoverOut:
                    freq = xo.XoverFreqOut
                else:
                    freq = dr.freq2Hz(self.listData[f"{bandName}_HPFrequency"])
                xoverBand.setHpfFreq(freq)
                xoverBand.setLpfType(self.listData[f"{bandName}_LPType"])
                if self.listData[f"{bandName}_LPFrequency"] == xo.XoverOut:
                    freq = xo.XoverFreqOut
                else:
                    freq = dr.freq2Hz(self.listData[f"{bandName}_LPFrequency"])
                xoverBand.setLpfFreq(freq)
                xoverBand.setGain(dr.dB2float(self.listData[f"{bandName}_Gain"]))
                xoverBand.setPolarity(self.listData[f"{bandName}_Polarity"])

                if band == ob.BandHigh:
                    self.crossover.setHigh(xoverBand)
                elif band == ob.BandMid:
                    self.crossover.setMid(xoverBand)
                elif band == ob.BandLow:
                    self.crossover.setLow(xoverBand)
        elif (
            self.listTarget.startswith(f"{peq.PeqBandHigh}\\{dr.ProtoValues}")
            or self.listTarget.startswith(f"{peq.PeqBandMid}\\{dr.ProtoValues}")
            or self.listTarget.startswith(f"{peq.PeqBandLow}\\{dr.ProtoValues}")
        ):
            band = "\\".join(self.listTarget.split("\\")[:-1])
            if band == peq.PeqBandHigh:
                try:
                    p = self.outHigh.peq
                except AttributeError:
                    p = self.outHigh.peq = peq.PA2Peq()

            elif band == peq.PeqBandMid:
                try:
                    p = self.outMid.peq
                except AttributeError:
                    p = self.outMid.peq = peq.PA2Peq()

            elif band == peq.PeqBandLow:
                try:
                    p = self.outLow.peq
                except AttributeError:
                    p = self.outLow.peq = peq.PA2Peq()
            else:
                raise ValueError(f"Invalid PEQ band received: {band}")

            if "ParametricEQ" in self.listData:
                if self.listData["ParametricEQ"] == peq.Enabled:
                    p.enable()
                else:
                    p.disable()
            for filtNumber in range(peq.FiltMinCount, peq.FiltMaxCount + 1):
                if f"Band_{filtNumber}_Type" in self.listData:
                    bandType = self.listData[f"Band_{filtNumber}_Type"]
                    freq = dr.freq2Hz(self.listData[f"Band_{filtNumber}_Frequency"])
                    q = float(self.listData[f"Band_{filtNumber}_Q"])
                    gain = dr.dB2float(self.listData[f"Band_{filtNumber}_Gain"])
                    if bandType == peq.Bell:
                        peqBand = peq.PA2PeqFilter(bandType, freq, gain, q)
                    elif bandType in (peq.LowShelf, peq.HighShelf):
                        slope = float(self.listData[f"Band_{filtNumber}_Slope"])
                        peqBand = peq.PA2PeqFilter(bandType, freq, gain, slope)
                    else:
                        raise ValueError(f"Invalid band type: {bandType}")
                    p.addFilter(peqBand, filtNumber=filtNumber)

            if band == peq.PeqBandHigh:
                self.outHigh.setPeq(p)
            elif band == peq.PeqBandMid:
                self.outMid.setPeq(p)
            elif band == peq.PeqBandLow:
                self.outLow.setPeq(p)

        elif (
            self.listTarget.startswith(f"{lim.High}\\{dr.ProtoValues}")
            or self.listTarget.startswith(f"{lim.Mid}\\{dr.ProtoValues}")
            or self.listTarget.startswith(f"{lim.Low}\\{dr.ProtoValues}")
        ):
            band = "\\".join(self.listTarget.split("\\")[:-1])
            if band == lim.High:
                try:
                    l = self.outHigh.limiter
                except AttributeError:
                    l = self.outHigh.limiter = lim.PA2Limiter()
            elif band == lim.Mid:
                try:
                    l = self.outMid.limiter
                except AttributeError:
                    l = self.outMid.limiter = lim.PA2Limiter()
            elif band == lim.Low:
                try:
                    l = self.outLow.limiter
                except AttributeError:
                    l = self.outLow.limiter = lim.PA2Limiter()
            else:
                raise ValueError(f"Invalid limiter band: {band}")

            if lim.State in self.listData:
                if self.listData[lim.State] == lim.Enabled:
                    l.enable()
                else:
                    l.disable()
            if "Threshold" in self.listData:
                l.setThreshold(dr.dB2float(self.listData["Threshold"]))
            if "OverEasy" in self.listData:
                if self.listData["OverEasy"] == lim.OverEasyOff:
                    l.setOverEasy(0)
                else:
                    l.setOverEasy(int(self.listData["OverEasy"]))

            if band == lim.High:
                self.outHigh.setLimiter(l)
            elif band == lim.Mid:
                self.outMid.setLimiter(l)
            elif band == lim.Low:
                self.outLow.setLimiter(l)

        elif (
            self.listTarget.startswith(f"{odly.High}\\{dr.ProtoValues}")
            or self.listTarget.startswith(f"{odly.Mid}\\{dr.ProtoValues}")
            or self.listTarget.startswith(f"{odly.Low}\\{dr.ProtoValues}")
        ):
            band = "\\".join(self.listTarget.split("\\")[:-1])
            if band == odly.High:
                try:
                    d = self.outHigh.delay
                except AttributeError:
                    d = self.outHigh.delay = odly.PA2OutputDelay()
            elif band == odly.Mid:
                try:
                    d = self.outMid.delay
                except AttributeError:
                    d = self.outMid.delay = odly.PA2OutputDelay()
            elif band == odly.Low:
                try:
                    d = self.outLow.delay
                except AttributeError:
                    d = self.outLow.delay = odly.PA2OutputDelay()
            else:
                raise ValueError(f"Invalid output delay band: {band}")

            if odly.Time in self.listData:
                d.setDelay(dr.time2sec(self.listData[odly.Time]) * 1000)
            if odly.State in self.listData:
                if self.listData[odly.State] == odly.Enabled:
                    d.enable()
                else:
                    d.disable()

            if band == odly.High:
                self.outHigh.setDelay(d)
            elif band == odly.Mid:
                self.outMid.setDelay(d)
            elif band == odly.Low:
                self.outLow.setDelay(d)

        del self.listTarget
        self.listData = {}
        self.blockingForList = False

    def _processCommand(self, message: str) -> None:
        command: Any = tssplit(message, delimiter=" ")
        argc = len(command)
        if argc == 0:
            return
        elif argc == 1:
            pass
        elif argc == 2:
            if command[0] == dr.ProtoList:
                self.listLock: str = dr.ProtoListEnd
                self.listTarget = command[1]
        elif argc == 3:
            if command[0] in (dr.ProtoGet, dr.ProtoSubResp):
                if command[1] == ProtoModel:
                    self.model = command[2]
                elif command[1] == ProtoVersion:
                    self.version = command[2]
                elif command[1] == ProtoName:
                    self.name = command[2]
                elif command[1].startswith(f"{ob.ProtoMutes}\\{dr.ProtoValues}"):
                    if command[1].endswith(ob.MuteLowL):
                        self.muteLowLeft: bool = command[2] == ob.MuteEnabled
                    elif command[1].endswith(ob.MuteLowR):
                        self.muteLowRight: bool = command[2] == ob.MuteEnabled
                    elif command[1].endswith(ob.MuteMidL):
                        self.muteMidLeft: bool = command[2] == ob.MuteEnabled
                    elif command[1].endswith(ob.MuteMidR):
                        self.muteMidRight: bool = command[2] == ob.MuteEnabled
                    elif command[1].endswith(ob.MuteHighL):
                        self.muteHighLeft: bool = command[2] == ob.MuteEnabled
                    elif command[1].endswith(ob.MuteHighR):
                        self.muteHighRight: bool = command[2] == ob.MuteEnabled
                elif (
                    command[1].startswith(f"{geq.GraphicEqSt}\\{dr.ProtoValues}")
                    or command[1].startswith(f"{geq.GraphicEqL}\\{dr.ProtoValues}")
                    or command[1].startswith(f"{geq.GraphicEqR}\\{dr.ProtoValues}")
                ):
                    if command[1].startswith(geq.GraphicEqSt):
                        channel = dr.ChannelsStereo
                    elif command[1].startswith(geq.GraphicEqL):
                        channel = dr.ChannelLeft
                    elif command[1].startswith(geq.GraphicEqR):
                        channel = dr.ChannelRight
                    else:
                        raise ValueError(f"Invalid channel: {command[1]}")

                    g = self.geqs[self._getValidGeq(channel)]

                    subtarget = command[1].rsplit("\\", 1)[1]
                    if subtarget == geq.Enable:
                        if command[2] == geq.Enabled:
                            g.enable()
                        else:
                            g.disable()
                    elif subtarget in geq.Band.values():
                        band = next(
                            key for key, value in geq.Band.items() if value == subtarget
                        )
                        g.setBand(band, dr.dB2float(command[2]))
                elif command[1].startswith(f"{afs.AFS}\\{dr.ProtoValues}"):
                    try:
                        self.autoFeedback
                    except AttributeError:
                        self.autoFeedback: afs.PA2Feedback = afs.PA2Feedback()

                    subtarget = command[1].rsplit("\\", 1)[1]
                    if subtarget == afs.Enable:
                        if command[2] == afs.Enabled:
                            self.autoFeedback.enable()
                        else:
                            self.autoFeedback.disable()
                    elif subtarget == afs.Filter:
                        self.autoFeedback.setMode(command[2])
                    elif subtarget == afs.Content:
                        self.autoFeedback.setType(command[2])
                    elif subtarget == afs.FixedFilters:
                        self.autoFeedback.setFixedFilters(int(command[2]))
                    elif subtarget == afs.LiftTime:
                        self.autoFeedback.setLiftTime(dr.time2sec(command[2]))
                elif command[1].startswith(f"{sub.Subharmonic}\\{dr.ProtoValues}"):
                    try:
                        self.subharmonic
                    except AttributeError:
                        self.subharmonic: sub.PA2Subharmonic = sub.PA2Subharmonic()

                    subtarget = command[1].rsplit("\\", 1)[1]
                    if subtarget == sub.Enable:
                        if command[2] == sub.Enabled:
                            self.subharmonic.enable()
                        else:
                            self.subharmonic.disable()
                    elif subtarget == sub.Harmonics:
                        self.subharmonic.setHarmonics(
                            dr.percent2float(command[2], multiplier=100)
                        )
                    elif subtarget == sub.Lows:
                        self.subharmonic.setLows(
                            dr.percent2float(command[2], multiplier=100)
                        )
                    elif subtarget == sub.Highs:
                        self.subharmonic.setHighs(
                            dr.percent2float(command[2], multiplier=100)
                        )
                elif command[1].startswith(f"{comp.Compressor}\\{dr.ProtoValues}"):
                    try:
                        self.compressor
                    except AttributeError:
                        self.compressor: comp.PA2Compressor = comp.PA2Compressor()

                    subtarget = command[1].rsplit("\\", 1)[1]
                    if subtarget == comp.Enable:
                        if command[2] == comp.Enabled:
                            self.compressor.enable()
                        else:
                            self.compressor.disable()
                    elif subtarget == comp.Threshold:
                        self.compressor.setThreshold(dr.dB2float(command[2]))
                    elif subtarget == comp.Gain:
                        self.compressor.setGain(dr.dB2float(command[2]))
                    elif subtarget == comp.Ratio:
                        numerator = dr.ratio2numerator(command[2])
                        if numerator == comp.Brickwall:
                            ratio = comp.RatioBrickwall
                        else:
                            ratio = float(numerator)
                        self.compressor.setRatio(ratio)
                    elif subtarget == comp.OverEasy:
                        self.compressor.setOverEasy(int(command[2]))
                elif command[1].startswith(f"{idly.InputDelay}\\{dr.ProtoValues}"):
                    try:
                        self.inputDelay
                    except AttributeError:
                        self.inputDelay: idly.PA2InputDelay = idly.PA2InputDelay()

                    subtarget = command[1].rsplit("\\", 1)[1]
                    if subtarget == idly.State:
                        if command[2] == idly.Enabled:
                            self.inputDelay.enable()
                        else:
                            self.inputDelay.disable()
                    elif subtarget == idly.Time:
                        self.inputDelay.setDelay(dr.time2sec(command[2]) * 1000)
                elif command[1].startswith(f"{rta.RTA}\\{dr.ProtoValues}"):
                    try:
                        self.rta
                    except AttributeError:
                        self.rta: rta.PA2Rta = rta.PA2Rta()

                    subtarget = command[1].rsplit("\\", 1)[1]
                    if subtarget == rta.Rate:
                        self.rta.setRate(command[2])
                    elif subtarget == rta.Offset:
                        self.rta.setOffset(dr.dB2float(command[2]))
                elif command[1].startswith(f"{gen.Generator}\\{dr.ProtoValues}"):
                    try:
                        self.generator
                    except AttributeError:
                        self.generator: gen.PA2Generator = gen.PA2Generator()

                    subtarget = command[1].rsplit("\\", 1)[1]
                    if subtarget == gen.Mode:
                        self.generator.setMode(command[2])
                    elif subtarget == gen.Level:
                        self.generator.setLevel(dr.dB2float(command[2]))

        # If we're currently blocking for this target,
        # indicate that we've received the response
        if argc > 1 and len(self.blockList) > 0:
            target = command[1]
            self._dprint(f"Checking for {target} in blockList")
            if target in self.blockList:
                self.blockList.pop(target)
                self._dprint(f"Received response for {target}")

    def _startThread(
        self,
        target: Callable[[], None],
        kwargs: Optional[Mapping[str, Any]] = None,
        daemon: bool = True,
    ) -> None:
        """Start a thread with the specified target and kwargs.
        Track the running threads in a queue so we can join them
        when exiting to ensure they complete properly.
        """

        thread = threading.Thread(target=target, kwargs=kwargs, daemon=daemon)
        thread.start()
        self.threads.put(thread)

    def _getValidGeq(self, channel: str) -> str:
        """Returns a key for the class's self.geqs{} to help
        validate the desired GEQ selection based on the device's
        actual stereo-linked or dual-mono configuration.

        Parameters
        ----------
        channel : str
            Left, right, or stereo.
            Value is one of dbxdriverack.ChannelsStereo,
            dbxdriverack.ChannelLeft, dbxdriverack.ChannelRight.

        Returns
        -------
        str
            "L", "R", or "St" indicating the validated GEQ selection.

        Raises
        ------
        ValueError
            If the desired GEQ selection does not match the
            live device configuration.
        """

        if self.stereoGeq and channel != dr.ChannelsStereo:
            raise ValueError("Stereo GEQ settings applied but channel specified")

        if self.stereoGeq:
            return "St"
        else:
            if channel == dr.ChannelsStereo:
                raise ValueError("GEQ Channel not specified for mono GEQ")

            if channel not in [dr.ChannelLeft, dr.ChannelRight]:
                raise ValueError(f"Invalid channel: {channel}")

            if channel == dr.ChannelLeft:
                return "L"
            elif channel == dr.ChannelRight:
                return "R"
            else:
                raise ValueError(f"Invalid channel: {channel}")

    def _hasConnectedTime(self) -> bool:
        try:
            self.connectedAt
        except AttributeError:
            return False

        return True

    def discoverDevices(
        self, srcPort: int = 0, dstPort: int = 19272, timeout: int = 5
    ) -> ItemsView[str, PA2Device]:
        """Solict and receive responses from all PA2 devices on the
        local network subnet. Returns a dictionary of discovered devices.

        Parameters
        ----------
        srcPort : int, optional
            UDP source port. By default the OS will pick a random port.
        dstPort : int, optional
            Destination UDP port to broadcast to. Defaults to 19272, used by PA2.
        timeout : int, optional
            Number of seconds to wait for DriveRacks to respond, by default 5.

        Returns
        -------
        ItemsView[str, PA2Device]
            Returns a dictionary of discovered devices. The key is the device's
            name and the value is a PA2Device object containing other details.
        """

        self.timeout = timeout
        self.discoveredDevices = {}
        if self._hasSocket():
            self._dprint("Socket already open, disconnecting before discovery")
            self._disconnect()
        self.socket = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socket.settimeout(timeout * 1.1)
        self.socket.bind(("", srcPort))

        self.connected = True
        self.connectedAt = datetime.now()

        self._startThread(self._readNetwork, kwargs={"mode": "udp"})
        self._startThread(self._processInputQueue, kwargs={"mode": "udp"})
        self._startThread(self._processOutputQueue, kwargs={"mode": "udp"})
        self._startThread(self._discoveryTimeout)

        dest = ("<broadcast>", dstPort)
        self.outputQueue.put((dest, "delay 100"))
        self.outputQueue.put((dest, f"{dr.ProtoGet} {ProtoModel}"))
        self.outputQueue.put((dest, f"{dr.ProtoGet} {ProtoName}"))
        self.outputQueue.put((dest, f"{dr.ProtoGet} {ProtoVersion}"))

        while self.connected:
            # block until the discovery process is complete
            pass

        return self.discoveredDevices.items()

    def connect(
        self,
        host: str,
        password: str = "administrator",
        port: int = 19272,
        timeout: int = 10,
    ) -> None:
        """Connect to a PA2 device.
        This also starts several threads that will handle sending and receiving
        messages to/from the device.

        Parameters
        ----------
        host : str
            IP address or hostname of the PA2 device.
            Use discoverDevices() to find devices on the local network.
        password : str, optional
            Password of a protected PA2.
            When no password is set, PA2 uses the default ("administrator")
        port : int, optional
            Port to connect to, by default 19272
        timeout : int, optional
            Seconds to wait for various network actions to complete. Default 10.
        """

        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout

        if self._openConnection():
            self._startThread(self._readNetwork)
            self._startThread(self._processInputQueue)
            self._startThread(self._processOutputQueue)
            self._authenticate()
            self._queueCommand(
                [dr.ProtoList, f"{Preset}"],
                block=True,
            )
            self._blockingQuery()

    def getName(self) -> str:
        """Get the device name of the connected PA2.

        Returns
        -------
        str
            Device name
        """

        return self.name

    def getModel(self) -> str:
        """Get the device model of the connected PA2.

        Returns
        -------
        str
            Device model
        """

        return self.model

    def getVersion(self) -> str:
        """Get the firmware version of the connected PA2.

        Returns
        -------
        str
            Firmware version
        """

        return self.version

    def getHost(self) -> str:
        """Get the IP address of the connected PA2.

        Returns
        -------
        str
            IP address
        """

        return self.host

    def getPort(self) -> int:
        """Get the TCP port of the connected PA2.

        Returns
        -------
        int
            Port number
        """

        return self.port

    def hasMids(self) -> bool:
        """Indicates whether the connected PA2 has Mid enabled
        by the setup wizard. This information is automatically
        queried during just following the authentication process.

        Returns
        -------
        bool
            True if the Mid band is enabled, False otherwise.
        """

        return self.numBands == 3 or self.numBands == 2 and self.lowMono

    def hasSubs(self) -> bool:
        """Indicates whether the connected PA2 has Low band enabled
        by the setup wizard. This information is automatically
        queried during just following the authentication process.

        Returns
        -------
        bool
            True if the Low band is enabled, False otherwise.
        """
        return self.numBands > 2 or self.lowMono

    def isLowMono(self) -> bool:
        """Indicates whether the connected PA2 has mono or stereo subwoofers
        set by the setup wizard. This information is automatically
        queried during just following the authentication process.

        Returns
        -------
        bool
            True if the Low band is mono, False if stereo.
        """

        return self.lowMono

    # GEQ

    def isGeqStereo(self) -> bool:
        """Indicates if the connected PA2 is set to use a stereo-linked GEQ
        or dual-mono GEQ. This information is automatically
        queried during just following the authentication process.

        Returns
        -------
        bool
            True if stereo-linked GEQ, False if dual-mono GEQ.
        """

        return self.stereoGeq

    def applyGeq(self, channel: str = dr.ChannelsStereo, block: bool = True) -> None:
        """Apply currently-set GEQ settings to the specified GEQ on the device.

        Parameters
        ----------
        channel : str, optional
            Which GEQ to apply to, by default dbxdriverack.ChannelsStereo
            Must be one of dbxdriverack.ChannelsStereo,
            dbxdriverack.ChannelLeft, dbxdriverack.ChannelRight.
        block : bool, optional
            Wait until device confirms completion
            before returning, by default True

        Raises
        ------
        ValueError
            No GEQ settings have been set
        """

        g = self.geqs[self._getValidGeq(channel)]

        if not g:
            raise ValueError("GEQ settings not set")

        for band, gain in g.bands.items():
            self._queueCommand(
                geq.CmdBuilder(
                    dr.ProtoSet,
                    geq.GeqBand,
                    channel=channel,
                    bandNumber=band,
                    value=gain,
                ).get()
            )

        self._queueCommand(
            geq.CmdBuilder(
                dr.ProtoSet,
                geq.Enable,
                channel=channel,
                value=g.enabled,
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    def setGeq(
        self, geqObj: geq.PA2Geq, channel: str = dr.ChannelsStereo, apply: bool = True
    ) -> None:
        """Sets a PA2's specified graphic EQ settings
        to match the provided PA2Geq object.

        Parameters
        ----------
        geqObj : geq.PA2Geq
            The GEQ settings to apply
        channel : str, optional
            Which GEQ to apply to, by default dbxdriverack.ChannelsStereo.
            Must be one of ChannelsStereo, ChannelLeft, ChannelRight.
        apply : bool, optional
            Whether to apply the values to the connected device. Default True.
            If False, just update the local state only (not typical).
        """

        self.geqs[self._getValidGeq(channel)] = geqObj

        if apply:
            self.applyGeq(channel=channel)

    def getGeq(
        self, channel: str = dr.ChannelsStereo, update: bool = True, block: bool = True
    ) -> geq.PA2Geq:
        """Get the currently-connected PA2's specified GEQ settings.

        Parameters
        ----------
        channel : str, optional
            Which GEQ to get, by default dbxdriverack.ChannelsStereo.
            Must be one of ChannelsStereo, ChannelLeft, ChannelRight.
        update : bool, optional
            Query the device for the latest GEQ settings, by default True.
            If False, just return the last known settings (not typical).
        block : bool, optional
            Wait until values are received from the device before returning.

        Returns
        -------
        geq.PA2Geq
            _description_
        """

        if update:
            self._queueCommand(
                geq.CmdBuilder(
                    dr.ProtoGet,
                    geq.Enable,
                    channel=channel,
                ).get(),
                block=True,
            )

            for band in geq.Band.keys():
                self._queueCommand(
                    geq.CmdBuilder(
                        dr.ProtoGet,
                        geq.GeqBand,
                        channel=channel,
                        bandNumber=band,
                    ).get(),
                    block=True,
                )

            self._blockingQuery()

        return self.geqs[self._getValidGeq(channel)]

    def geqChangeMode(
        self, mode: str, channel: str = dr.ChannelsStereo, block: bool = True
    ) -> None:
        """Immediately set the live GEQ mode of the connected PA2.

        Parameters
        ----------
        mode : str
            GEQ mode to set. Must be one of:
                geq.ModeFlat, geq.ModeMyBand, geq.ModeSpeech,
                geq.ModeVenue, geq.ModeDJ, geq.ModeManual
        channel : str, optional
            Which GEQ to apply to, by default dbxdriverack.ChannelsStereo.
            Must be one of ChannelsStereo, ChannelLeft, ChannelRight.
        block : bool, optional
            Wait until device confirms completion before returning. Default True

        Raises
        ------
        ValueError
            Invalid mode
        """

        if mode not in [
            geq.ModeFlat,
            geq.ModeMyBand,
            geq.ModeSpeech,
            geq.ModeVenue,
            geq.ModeDJ,
            geq.ModeManual,
        ]:
            raise ValueError(f"Invalid mode: {mode}")
        self._queueCommand(
            geq.CmdBuilder(
                dr.ProtoSet,
                geq.Mode,
                channel=channel,
                value=mode,
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    # AEQ

    def applyAeq(self, block: bool = True) -> None:
        """Apply the currently-set AutoEQ filters to the connected PA2.
        EQ will be flattened before applying the AutoEQ.

        Parameters
        ----------
        block : bool, optional
            Wait until the device confirms completion. Default True.

        Raises
        ------
        ValueError
            Auto EQ settings not set
        """

        try:
            self.autoEq
        except AttributeError:
            raise ValueError("Auto EQ settings not set")

        self._queueCommand(
            aeq.CmdBuilder(
                dr.ProtoSet,
                aeq.Enable,
                value=self.autoEq.enabled,
            ).get()
        )

        # Flatten the AutoEQ
        self._queueCommand(
            aeq.CmdBuilder(
                dr.ProtoSet,
                aeq.Mode,
                value=aeq.ModeFlat,
            ).get()
        )

        for filtNumber, aeqFilter in self.autoEq.filters.items():
            # type
            self._queueCommand(
                aeq.CmdBuilder(
                    dr.ProtoSet,
                    aeq.AutoEqType,
                    filtNumber=filtNumber,
                    value=aeqFilter.filtType,
                ).get()
            )
            self._queueCommand(
                aeq.CmdBuilder(
                    dr.ProtoSet,
                    aeq.AutoEqFreq,
                    filtNumber=filtNumber,
                    value=aeqFilter.freq,
                ).get()
            )
            self._queueCommand(
                aeq.CmdBuilder(
                    dr.ProtoSet,
                    aeq.AutoEqQ,
                    filtNumber=filtNumber,
                    value=aeqFilter.q,
                ).get()
            )
            self._queueCommand(
                aeq.CmdBuilder(
                    dr.ProtoSet,
                    aeq.AutoEqGain,
                    filtNumber=filtNumber,
                    value=aeqFilter.gain,
                ).get(),
                block=block,
            )

        if block:
            self._blockingQuery()

    def setAeq(self, aeq: aeq.PA2AutoEq, apply: bool = True) -> None:
        """Sets a PA2's specified AutoEQ settings to match
        the provided PA2AutoEq object.

        Parameters
        ----------
        aeq : aeq.PA2AutoEq
            The AutoEQ settings to apply
        apply : bool, optional
            Whether to apply the values to the connected device. Default True.
            If False, just update the local state only (not typical).
        """

        self.autoEq = aeq

        if apply:
            self.applyAeq()

    def aeqChangeMode(self, mode: str, block: bool = True) -> None:
        """Immediately set the live AutoEQ mode of the connected PA2.

        Parameters
        ----------
        mode : str
            AutoEQ mode to set. Must be one of:
                aeq.ModeFlat, aeq.ModeManual, aeq.ModeAuto
        block : bool, optional
            Wait until device confirms completion before returning. Default True

        Raises
        ------
        ValueError
            Invalid mode
        """

        if mode not in [aeq.ModeFlat, aeq.ModeManual, aeq.ModeAuto]:
            raise ValueError(f"Invalid mode: {mode}")
        self._queueCommand(
            aeq.CmdBuilder(
                dr.ProtoSet,
                aeq.Mode,
                value=mode,
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    def getAeq(self, update: bool = True, block: bool = True) -> aeq.PA2AutoEq:
        """Get the currently-connected PA2's specified AutoEQ settings.

        Parameters
        ----------
        update : bool, optional
            Query the device for the latest AutoEQ settings, by default True.
            If False, just return the last known settings (not typical).
        block : bool, optional
            Wait until values are received from the device. Default True.

        Returns
        -------
        aeq.PA2AutoEq
            AutoEQ settings
        """

        if update:
            self._queueCommand(
                [dr.ProtoList, f"{aeq.AutoEq}\\{dr.ProtoValues}"],
                block=block,
            )
            if block:
                self._blockingQuery()

        return self.autoEq

    # AFS

    def applyAfs(self, block: bool = True) -> None:
        """Apply the currently-set Advanced Feedback Suppression
        settings to the connected PA2.

        Parameters
        ----------
        block : bool, optional
            Wait until the device confirms completion. Default True.

        Raises
        ------
        ValueError
            Auto Feedback settings not set
        """

        if not self.autoFeedback:
            raise ValueError("Auto Feedback settings not set")

        self._queueCommand(
            afs.CmdBuilder(
                dr.ProtoSet,
                afs.Filter,
                value=self.autoFeedback.mode,
            ).get()
        )

        self._queueCommand(
            afs.CmdBuilder(
                dr.ProtoSet,
                afs.Content,
                value=self.autoFeedback.type,
            ).get()
        )

        self._queueCommand(
            afs.CmdBuilder(
                dr.ProtoSet,
                afs.FixedFilters,
                value=self.autoFeedback.fixedFilters,
            ).get()
        )

        self._queueCommand(
            afs.CmdBuilder(
                dr.ProtoSet,
                afs.LiftTime,
                value=self.autoFeedback.liftTime,
            ).get(),
        )

        self._queueCommand(
            afs.CmdBuilder(
                dr.ProtoSet,
                afs.Enable,
                value=self.autoFeedback.enabled,
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    def setAfs(self, afsObj: afs.PA2Feedback, apply: bool = True) -> None:
        """Sets a PA2's AFS settings to match the provided PA2Feedback object.

        Parameters
        ----------
        afsObj : afs.PA2Feedback
            The AFS settings to apply
        apply : bool, optional
            Whether to apply the values to the connected device. Default True.
            If False, just update the local state only (not typical).
        """

        self.autoFeedback = afsObj

        if apply:
            self.applyAfs()

    def afsChangeMode(self, mode: str, block: bool = True) -> None:
        """Immediately set the live AFS mode of the connected PA2.

        Parameters
        ----------
        mode : str
            AFS mode to set. Must be one of:
                afs.ModeLive, afs.ModeFixed
        block : bool, optional
            Wait until device confirms completion before returning. Default True

        Raises
        ------
        ValueError
            Invalid mode
        """

        if mode not in [afs.ModeLive, afs.ModeFixed]:
            raise ValueError("Invalid mode")
        self._queueCommand(
            afs.CmdBuilder(
                dr.ProtoSet,
                afs.Filter,
                value=mode,
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    def afsChangeType(self, type: str, block: bool = True) -> None:
        """Immediately set the live AFS program type of the connected PA2.

        Parameters
        ----------
        type : str
            AFS program type to set. Must be one of:
                afs.TypeSpeech, afs.TypeMusic, afs.TypeSpeechMusic
        block : bool, optional
            Wait until device confirms completion before returning. Default True

        Raises
        ------
        ValueError
            Invalid type
        """

        if type not in [afs.TypeSpeech, afs.TypeMusic, afs.TypeSpeechMusic]:
            raise ValueError("Invalid type")
        self._queueCommand(
            afs.CmdBuilder(
                dr.ProtoSet,
                afs.Content,
                value=type,
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    def afsClearLive(self, block: bool = True) -> None:
        """Immediately clear the live AFS filters of the connected PA2.

        Parameters
        ----------
        block : bool, optional
            Wait until device confirms completion before returning. Default True
        """

        self._queueCommand(
            afs.CmdBuilder(
                dr.ProtoSet,
                afs.ClearLive,
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    def afsClearAll(self, block: bool = True) -> None:
        """Immediately clear all AFS filters of the connected PA2.

        Parameters
        ----------
        block : bool, optional
            Wait until device confirms completion before returning. Default True
        """

        self._queueCommand(
            afs.CmdBuilder(
                dr.ProtoSet,
                afs.ClearAll,
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    def afsLiveLift(self, block: bool = True) -> None:
        """Immediately lift the live AFS filters of the connected PA2.

        Parameters
        ----------
        block : bool, optional
            Wait until device confirms completion before returning. Default True
        """

        self._queueCommand(
            afs.CmdBuilder(
                dr.ProtoSet,
                afs.LiveLift,
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    def getAfs(self, update: bool = True, block: bool = True) -> afs.PA2Feedback:
        """Get the currently-connected PA2's specified AFS settings.

        Parameters
        ----------
        update : bool, optional
            Query the device for the latest AFS settings, by default True.
            If False, just return the last known settings (not typical).
        block : bool, optional
            Wait until values are received from the device. Default True.

        Returns
        -------
        afs.PA2Feedback
            AFS settings
        """

        if update:
            self._queueCommand(
                afs.CmdBuilder(
                    dr.ProtoGet,
                    afs.Filter,
                ).get(),
                block=block,
            )

            self._queueCommand(
                afs.CmdBuilder(
                    dr.ProtoGet,
                    afs.Content,
                ).get(),
                block=block,
            )

            self._queueCommand(
                afs.CmdBuilder(
                    dr.ProtoGet,
                    afs.FixedFilters,
                ).get(),
                block=block,
            )

            self._queueCommand(
                afs.CmdBuilder(
                    dr.ProtoGet,
                    afs.LiftTime,
                ).get(),
                block=block,
            )

            self._queueCommand(
                afs.CmdBuilder(
                    dr.ProtoGet,
                    afs.Enable,
                ).get(),
                block=block,
            )

            self._blockingQuery()

        return self.autoFeedback

    # Subharmonic Synth

    def applySubharmonic(self, block: bool = True) -> None:
        """Apply the currently-set Subharmonic Synth
        settings to the connected PA2.

        Parameters
        ----------
        block : bool, optional
            Wait until the device confirms completion. Default True.

        Raises
        ------
        ValueError
            Subharmonic settings not set
        """

        try:
            self.subharmonic
        except AttributeError:
            raise ValueError("Subharmonic settings not set")

        self._queueCommand(
            sub.CmdBuilder(
                dr.ProtoSet,
                sub.Harmonics,
                value=self.subharmonic.harmonics,
            ).get()
        )

        self._queueCommand(
            sub.CmdBuilder(
                dr.ProtoSet,
                sub.Lows,
                value=self.subharmonic.lows,
            ).get()
        )

        self._queueCommand(
            sub.CmdBuilder(
                dr.ProtoSet,
                sub.Highs,
                value=self.subharmonic.highs,
            ).get(),
        )

        self._queueCommand(
            sub.CmdBuilder(
                dr.ProtoSet,
                sub.Enable,
                value=self.subharmonic.enabled,
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    def setSubharmonic(
        self, subharmonic: sub.PA2Subharmonic, apply: bool = True
    ) -> None:
        """Sets a PA2's Subharmonic Synth settings to match
        the provided PA2Subharmonic object.

        Parameters
        ----------
        subharmonic : sub.PA2Subharmonic
            The Subharmonic Synth settings to apply
        apply : bool, optional
            Whether to apply the values to the connected device. Default True.
            If False, just update the local state only (not typical).
        """

        self.subharmonic = subharmonic

        if apply:
            self.applySubharmonic()

    def getSubharmonic(
        self, update: bool = True, block: bool = True
    ) -> sub.PA2Subharmonic:
        """Get the currently-connected PA2's specified
        Subharmonic Synth settings.

        Parameters
        ----------
        update : bool, optional
            Query the device for the latest Subharmonic settings. Default True.
            If False, just return the last known settings (not typical).
        block : bool, optional
            Wait until values are received from the device. Default True.

        Returns
        -------
        sub.PA2Subharmonic
            Subharmonic Synth settings
        """

        if update:
            self._queueCommand(
                sub.CmdBuilder(
                    dr.ProtoGet,
                    sub.Harmonics,
                ).get(),
                block=block,
            )

            self._queueCommand(
                sub.CmdBuilder(
                    dr.ProtoGet,
                    sub.Lows,
                ).get(),
                block=block,
            )

            self._queueCommand(
                sub.CmdBuilder(
                    dr.ProtoGet,
                    sub.Highs,
                ).get(),
                block=block,
            )

            self._queueCommand(
                sub.CmdBuilder(
                    dr.ProtoGet,
                    sub.Enable,
                ).get(),
                block=block,
            )

            self._blockingQuery()

        return self.subharmonic

    # Compressor

    def applyCompressor(self, block: bool = True) -> None:
        """Apply the currently-set Compressor settings to the connected PA2.

        Parameters
        ----------
        block : bool, optional
            Wait until the device confirms completion. Default True.

        Raises
        ------
        ValueError
            Compressor settings not set
        """

        try:
            self.compressor
        except AttributeError:
            raise ValueError("Compressor settings not set")

        self._queueCommand(
            comp.CmdBuilder(
                dr.ProtoSet,
                comp.Threshold,
                value=self.compressor.threshold,
            ).get()
        )

        self._queueCommand(
            comp.CmdBuilder(
                dr.ProtoSet,
                comp.Gain,
                value=self.compressor.gain,
            ).get()
        )

        self._queueCommand(
            comp.CmdBuilder(
                dr.ProtoSet,
                comp.Ratio,
                value=self.compressor.ratio,
            ).get()
        )

        self._queueCommand(
            comp.CmdBuilder(
                dr.ProtoSet,
                comp.OverEasy,
                value=self.compressor.overEasy,
            ).get()
        )

        self._queueCommand(
            comp.CmdBuilder(
                dr.ProtoSet,
                comp.Enable,
                value=self.compressor.enabled,
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    def setCompressor(self, compressor: comp.PA2Compressor, apply: bool = True) -> None:
        """Sets a PA2's Compressor settings to match
        the provided PA2Compressor object.

        Parameters
        ----------
        compressor : comp.PA2Compressor
            The Compressor settings to apply
        apply : bool, optional
            Whether to apply the values to the connected device. Default True.
            If False, just update the local state only (not typical).
        """

        self.compressor = compressor

        if apply:
            self.applyCompressor()

    def getCompressor(
        self, update: bool = True, block: bool = True
    ) -> comp.PA2Compressor:
        """Get the currently-connected PA2's specified Compressor settings.

        Parameters
        ----------
        update : bool, optional
            Query the device for the latest Compressor settings. Default True.
            If False, just return the last known settings (not typical).
        block : bool, optional
            Wait until values are received from the device. Default True.

        Returns
        -------
        comp.PA2Compressor
            Compressor settings
        """

        if update:
            self._queueCommand(
                comp.CmdBuilder(
                    dr.ProtoGet,
                    comp.Threshold,
                ).get(),
                block=block,
            )

            self._queueCommand(
                comp.CmdBuilder(
                    dr.ProtoGet,
                    comp.Gain,
                ).get(),
                block=block,
            )

            self._queueCommand(
                comp.CmdBuilder(
                    dr.ProtoGet,
                    comp.Ratio,
                ).get(),
                block=block,
            )

            self._queueCommand(
                comp.CmdBuilder(
                    dr.ProtoGet,
                    comp.OverEasy,
                ).get(),
                block=block,
            )

            self._queueCommand(
                comp.CmdBuilder(
                    dr.ProtoGet,
                    comp.Enable,
                ).get(),
                block=block,
            )

            self._blockingQuery()

        return self.compressor

    # Input Delay

    def applyInputDelay(self, block: bool = True) -> None:
        """Apply the currently-set Input Delay settings to the connected PA2.

        Parameters
        ----------
        block : bool, optional
            Wait until the device confirms completion. Default True.

        Raises
        ------
        ValueError
            Input Delay settings not set
        """

        if not self.inputDelay:
            raise ValueError("Input Delay settings not set")

        self._queueCommand(
            idly.CmdBuilder(
                dr.ProtoSet,
                idly.Time,
                value=self.inputDelay.delay,
            ).get()
        )

        self._queueCommand(
            idly.CmdBuilder(
                dr.ProtoSet,
                idly.State,
                value=self.inputDelay.enabled,
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    def setInputDelay(self, delay: idly.PA2InputDelay, apply: bool = True) -> None:
        """Sets a PA2's Input Delay settings to match
        the provided PA2InputDelay object.

        Parameters
        ----------
        delay : idly.PA2InputDelay
            The Input Delay settings to apply
        apply : bool, optional
            Whether to apply the values to the connected device. Default True.
            If False, just update the local state only (not typical).
        """

        self.inputDelay = delay

        if apply:
            self.applyInputDelay()

    def getInputDelay(
        self, update: bool = True, block: bool = True
    ) -> idly.PA2InputDelay:
        """Get the currently-connected PA2's specified Input Delay settings.

        Parameters
        ----------
        update : bool, optional
            Query the device for the latest Input Delay settings. Default True.
            If False, just return the last known settings (not typical).
        block : bool, optional
            _description_, by default True

        Returns
        -------
        idly.PA2InputDelay
            Input Delay settings
        """

        if update:
            self._queueCommand(
                idly.CmdBuilder(
                    dr.ProtoGet,
                    idly.Time,
                ).get(),
                block=block,
            )

            self._queueCommand(
                idly.CmdBuilder(
                    dr.ProtoGet,
                    idly.State,
                ).get(),
                block=block,
            )

            self._blockingQuery()

        return self.inputDelay

    # Crossover

    def applyCrossover(self, block: bool = True) -> None:
        """Apply the currently-set Crossover settings to the connected PA2.

        Parameters
        ----------
        block : bool, optional
            Wait until the device confirms completion. Default True.

        Raises
        ------
        ValueError
            Crossover settings not set or invalid band
        """

        try:
            self.crossover
        except AttributeError:
            raise ValueError("Crossover settings not set")

        for band in [ob.BandHigh, ob.BandMid, ob.BandLow]:
            if band == ob.BandHigh:
                try:
                    crossover = self.crossover.bandHigh
                except:
                    continue
            elif band == ob.BandMid:
                try:
                    crossover = self.crossover.bandMid
                except:
                    continue
            elif band == ob.BandLow:
                try:
                    crossover = self.crossover.bandLow
                except:
                    continue
            else:
                raise ValueError(f"Invalid band: {band}")

            # Begin with HPF at -inf and LPF at inf
            # so DriveRack's current running state doesn't limit the other's range
            self._queueCommand(
                xo.CmdBuilder(
                    dr.ProtoSet,
                    xo.XoverHPFrequency,
                    band=band,
                    lowMono=self.lowMono,
                    value=xo.XoverFreqOut,
                ).get()
            )
            self._queueCommand(
                xo.CmdBuilder(
                    dr.ProtoSet,
                    xo.XoverLPFrequency,
                    band=band,
                    lowMono=self.lowMono,
                    value=xo.XoverFreqOut,
                ).get()
            )

            self._queueCommand(
                xo.CmdBuilder(
                    dr.ProtoSet,
                    xo.XoverPolarity,
                    band=band,
                    lowMono=self.lowMono,
                    value=crossover.polarity,
                ).get()
            )
            self._queueCommand(
                xo.CmdBuilder(
                    dr.ProtoSet,
                    xo.XoverHPType,
                    band=band,
                    lowMono=self.lowMono,
                    value=crossover.hpfType,
                ).get()
            )
            self._queueCommand(
                xo.CmdBuilder(
                    dr.ProtoSet,
                    xo.XoverLPType,
                    band=band,
                    lowMono=self.lowMono,
                    value=crossover.lpfType,
                ).get()
            )
            self._queueCommand(
                xo.CmdBuilder(
                    dr.ProtoSet,
                    xo.XoverGain,
                    band=band,
                    lowMono=self.lowMono,
                    value=crossover.gain,
                ).get()
            )
            self._queueCommand(
                xo.CmdBuilder(
                    dr.ProtoSet,
                    xo.XoverHPFrequency,
                    band=band,
                    lowMono=self.lowMono,
                    value=crossover.hpfFreq,
                ).get()
            )
            self._queueCommand(
                xo.CmdBuilder(
                    dr.ProtoSet,
                    xo.XoverLPFrequency,
                    band=band,
                    lowMono=self.lowMono,
                    value=crossover.lpfFreq,
                ).get(),
                block=block,
            )

        if block:
            self._blockingQuery()

    def setCrossover(self, crossover: xo.PA2Crossover, apply: bool = True) -> None:
        """Sets a PA2's Crossover settings to match
        the provided PA2Crossover object.

        Parameters
        ----------
        crossover : xo.PA2Crossover
            The Crossover settings to apply
        apply : bool, optional
            Whether to apply the values to the connected device. Default True.
            If False, just update the local state only (not typical).
        """
        self.crossover = crossover

        if apply:
            self.applyCrossover()

    def getCrossover(self, update: bool = True, block: bool = True) -> xo.PA2Crossover:
        """Get the currently-connected PA2's specified Crossover settings.

        Parameters
        ----------
        update : bool, optional
            Query the device for the latest Crossover settings. Default True.
            If False, just return the last known settings (not typical).
        block : bool, optional
            Wait until values are received from the device. Default True.

        Returns
        -------
        xo.PA2Crossover
            Crossover settings
        """

        if update:
            self._queueCommand(
                [dr.ProtoList, f"{xo.ProtoCrossover}\\{dr.ProtoValues}"],
                block=block,
            )
            if block:
                self._blockingQuery()

        return self.crossover

    # PEQ

    def applyPeqs(self, block: bool = True) -> None:
        """Apply any currently-set PEQ settings to the connected PA2.

        Parameters
        ----------
        block : bool, optional
            Wait until the device confirms completion. Default True.
        """

        for band in [ob.BandHigh, ob.BandMid, ob.BandLow]:
            if band == ob.BandHigh:
                try:
                    output = self.outHigh
                except AttributeError:
                    continue
            elif band == ob.BandMid and (
                self.numBands == 3 or self.numBands == 2 and self.lowMono
            ):
                try:
                    output = self.outMid
                except AttributeError:
                    continue
            elif band == ob.BandLow and (self.numBands > 2 or self.lowMono):
                try:
                    output = self.outLow
                except AttributeError:
                    continue
            else:
                continue

            if hasattr(output, "peq"):
                # Flatten the PEQ
                self._queueCommand(
                    peq.CmdBuilder(
                        dr.ProtoSet, peq.PeqFlat, band=band, value=peq.Flat
                    ).get()
                )

                for filtNumber, peqBand in output.peq.filters.items():
                    # type
                    self._queueCommand(
                        peq.CmdBuilder(
                            dr.ProtoSet,
                            peq.PeqType,
                            band=band,
                            filtNumber=filtNumber,
                            value=peqBand.filtType,
                        ).get()
                    )

                    # frequency
                    self._queueCommand(
                        peq.CmdBuilder(
                            dr.ProtoSet,
                            peq.PeqFreq,
                            band=band,
                            filtNumber=filtNumber,
                            value=peqBand.freq,
                        ).get()
                    )

                    # Q/slope
                    if peqBand.filtType in [peq.LowShelf, peq.HighShelf]:
                        self._queueCommand(
                            peq.CmdBuilder(
                                dr.ProtoSet,
                                peq.PeqSlope,
                                band=band,
                                filtNumber=filtNumber,
                                value=peqBand.q,
                            ).get()
                        )
                    elif peqBand.filtType == peq.Bell:
                        self._queueCommand(
                            peq.CmdBuilder(
                                dr.ProtoSet,
                                peq.PeqQ,
                                band=band,
                                filtNumber=filtNumber,
                                value=peqBand.q,
                            ).get()
                        )

                    # gain
                    self._queueCommand(
                        peq.CmdBuilder(
                            dr.ProtoSet,
                            peq.PeqGain,
                            band=band,
                            filtNumber=filtNumber,
                            value=peqBand.gain,
                        ).get()
                    )

                # enable
                self._queueCommand(
                    peq.CmdBuilder(
                        dr.ProtoSet,
                        peq.PeqEnable,
                        band=band,
                        value=output.peq.enabled,
                    ).get(),
                    block=block,
                )

        if block:
            self._blockingQuery()

    def setPeq(self, band: str, eq: peq.PA2Peq, apply: bool = True) -> None:
        """Sets a PA2's PEQ settings to match the provided PA2Peq object.

        Parameters
        ----------
        band : str
            Which band to apply the PEQ to. Must be one of:
                dbxdriverack.BandHigh, BandMid, BandLow
        eq : peq.PA2Peq
            The PEQ settings to apply
        apply : bool, optional
            Whether to apply the values to the connected device. Default True.
            If False, just update the local state only (not typical).
        """

        if band == ob.BandHigh:
            self.outHigh.setPeq(eq)
        elif band == ob.BandMid:
            self.outMid.setPeq(eq)
        elif band == ob.BandLow:
            self.outLow.setPeq(eq)

        if apply:
            self.applyPeqs()

    def flattenPeq(self, band: str, apply: bool = True, block: bool = True) -> None:
        """Sets all PEQ filters to flat for the specified band.
        By default, also update the live device to reflect the change.

        Parameters
        ----------
        band : str
            Which band's PEQ to flatten. Must be one of:
                dbxdriverack.BandHigh, BandMid, BandLow
        apply : bool, optional
            Whether to apply the values to the connected device. Default True.
            If False, just update the local state only (not typical).
        block : bool, optional
            Wait until the device confirms completion. Default True.
        """

        if band == ob.BandHigh:
            self.outHigh.peq.flatten()
        elif band == ob.BandMid:
            self.outMid.peq.flatten()
        elif band == ob.BandLow:
            self.outLow.peq.flatten()

        if apply:
            self._queueCommand(
                peq.CmdBuilder(
                    dr.ProtoSet, peq.PeqFlat, band=band, value=peq.Flat
                ).get(),
                block=block,
            )

            if block:
                self._blockingQuery()

    def unflattenPeq(self, band: str, block: bool = True) -> None:
        """Immediately restore the PEQ to the previous state, before flattened.
        This uses a device-internal state to operate, so it depends on having
        no alterations since the last flattening to work.

        This command does not update the local state of the PEQ after restoring.

        Parameters
        ----------
        band : str
            Which band's PEQ to unflatten. Must be one of:
                dbxdriverack.BandHigh, BandMid, BandLow
        block : bool, optional
            Wait until the device confirms completion. Default True.
        """

        self._queueCommand(
            peq.CmdBuilder(
                dr.ProtoSet, peq.PeqFlat, band=band, value=peq.Restore
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    def getPeq(self, band: str, update: bool = True, block: bool = True) -> peq.PA2Peq:
        """Get the currently-connected PA2's specified PEQ settings.

        Parameters
        ----------
        band : str
            Which band's PEQ to get. Must be one of:
                dbxdriverack.BandHigh, BandMid, BandLow
        update : bool, optional
            Query the device for the latest PEQ settings. Default True.
            If False, just return the last known settings (not typical).
        block : bool, optional
            Wait until values are received from the device. Default True.

        Returns
        -------
        peq.PA2Peq
            PEQ settings

        Raises
        ------
        ValueError
            Invalid band
        """

        if update:
            if band == ob.BandHigh:
                target = peq.PeqBandHigh
            elif band == ob.BandMid:
                target = peq.PeqBandMid
            elif band == ob.BandLow:
                target = peq.PeqBandLow
            else:
                raise ValueError(f"Invalid band: {band}")

            self._queueCommand(
                [dr.ProtoList, f"{target}\\{dr.ProtoValues}"],
                block=block,
            )
            if block:
                self._blockingQuery()

        if band == ob.BandHigh:
            return self.outHigh.peq
        elif band == ob.BandMid:
            return self.outMid.peq
        elif band == ob.BandLow:
            return self.outLow.peq
        else:
            raise ValueError(f"Invalid band: {band}")

    # Limiter

    def applyLimiters(self, block: bool = True) -> None:
        """Apply any currently-set Limiter settings to the connected PA2.

        Parameters
        ----------
        block : bool, optional
            Wait until the device confirms completion. Default True.

        Raises
        ------
        ValueError
            Invalid band
        """

        for band in [ob.BandHigh, ob.BandMid, ob.BandLow]:
            if band == ob.BandHigh:
                try:
                    limiter = self.outHigh.limiter
                except AttributeError:
                    continue
            elif band == ob.BandMid:
                try:
                    limiter = self.outMid.limiter
                except AttributeError:
                    continue
            elif band == ob.BandLow:
                try:
                    limiter = self.outLow.limiter
                except AttributeError:
                    continue
            else:
                raise ValueError(f"Invalid band: {band}")

            if limiter:
                self._queueCommand(
                    lim.CmdBuilder(
                        dr.ProtoSet,
                        lim.Thresh,
                        band=band,
                        value=limiter.threshold,
                    ).get()
                )
                self._queueCommand(
                    lim.CmdBuilder(
                        dr.ProtoSet,
                        lim.OverEasy,
                        band=band,
                        value=limiter.overEasy,
                    ).get()
                )
                self._queueCommand(
                    lim.CmdBuilder(
                        dr.ProtoSet,
                        lim.State,
                        band=band,
                        value=limiter.enabled,
                    ).get(),
                    block=block,
                )
        if block:
            self._blockingQuery()

    def setLimiter(
        self, band: str, limiter: lim.PA2Limiter, apply: bool = True
    ) -> None:
        """Sets a PA2's Limiter settings to match
        the provided PA2Limiter object.

        Parameters
        ----------
        band : str
            Which band to apply the Limiter to. Must be one of:
                dbxdriverack.BandHigh, BandMid, BandLow
        limiter : lim.PA2Limiter
            The Limiter settings to apply
        apply : bool, optional
            Whether to apply the values to the connected device. Default True.
            If False, just update the local state only (not typical).
        """

        if band == ob.BandHigh:
            self.outHigh.setLimiter(limiter)
        elif band == ob.BandMid:
            self.outMid.setLimiter(limiter)
        elif band == ob.BandLow:
            self.outLow.setLimiter(limiter)

        if apply:
            self.applyLimiters()

    def getLimiter(
        self, band: str, update: bool = True, block: bool = True
    ) -> lim.PA2Limiter:
        """Get the currently-connected PA2's specified Limiter settings.

        Parameters
        ----------
        band : str
            Which band's Limiter to get. Must be one of:
                dbxdriverack.BandHigh, BandMid, BandLow
        update : bool, optional
            Query the device for the latest Limiter settings. Default True.
            If False, just return the last known settings (not typical).
        block : bool, optional
            Wait until values are received from the device. Default True.

        Returns
        -------
        lim.PA2Limiter
            Limiter settings

        Raises
        ------
        ValueError
            Invalid band
        """

        if update:
            if band == ob.BandHigh:
                target = lim.High
            elif band == ob.BandMid:
                target = lim.Mid
            elif band == ob.BandLow:
                target = lim.Low
            else:
                raise ValueError(f"Invalid band: {band}")

            self._queueCommand(
                [dr.ProtoList, f"{target}\\{dr.ProtoValues}"],
                block=block,
            )
            if block:
                self._blockingQuery()

        if band == ob.BandHigh:
            return self.outHigh.limiter
        elif band == ob.BandMid:
            return self.outMid.limiter
        elif band == ob.BandLow:
            return self.outLow.limiter
        else:
            raise ValueError(f"Invalid band: {band}")

    # Output/Alignment Delay

    def applyOutputDelays(self, block: bool = True) -> None:
        """Apply any currently-set Output Delay settings to the connected PA2.

        Parameters
        ----------
        block : bool, optional
            Wait until the device confirms completion. Default True.

        Raises
        ------
        ValueError
            Invalid band
        """

        for band in [ob.BandHigh, ob.BandMid, ob.BandLow]:
            if band == ob.BandHigh:
                try:
                    outputDelay = self.outHigh.delay
                except AttributeError:
                    continue
            elif band == ob.BandMid:
                try:
                    outputDelay = self.outMid.delay
                except AttributeError:
                    continue
            elif band == ob.BandLow:
                try:
                    outputDelay = self.outLow.delay
                except AttributeError:
                    continue
            else:
                raise ValueError(f"Invalid band: {band}")

            if outputDelay:
                self._queueCommand(
                    odly.CmdBuilder(
                        dr.ProtoSet,
                        odly.Time,
                        band=band,
                        value=outputDelay.delay,
                    ).get()
                )
                self._queueCommand(
                    odly.CmdBuilder(
                        dr.ProtoSet,
                        odly.State,
                        band=band,
                        value=outputDelay.enabled,
                    ).get(),
                    block=block,
                )
        if block:
            self._blockingQuery()

    def setOutputDelay(
        self, band: str, delay: odly.PA2OutputDelay, apply: bool = True
    ) -> None:
        """Sets a PA2's Output Delay settings to match
        the provided PA2OutputDelay object.

        Parameters
        ----------
        band : str
            Which band to apply the Output Delay to. Must be one of:
                dbxdriverack.BandHigh, BandMid, BandLow
        delay : odly.PA2OutputDelay
            The Output Delay settings to apply
        apply : bool, optional
            Whether to apply the values to the connected device. Default True.
            If False, just update the local state only (not typical).
        """

        if band == ob.BandHigh:
            self.outHigh.setDelay(delay)
        elif band == ob.BandMid:
            self.outMid.setDelay(delay)
        elif band == ob.BandLow:
            self.outLow.setDelay(delay)

        if apply:
            self.applyOutputDelays()

    def getOutputDelay(
        self, band: str, update: bool = True, block: bool = True
    ) -> odly.PA2OutputDelay:
        """Get the currently-connected PA2's specified Output Delay settings.

        Parameters
        ----------
        band : str
            Which band's Output Delay to get. Must be one of:
                dbxdriverack.BandHigh, BandMid, BandLow
        update : bool, optional
            Query the device for the latest Output Delay settings. Default True.
            If False, just return the last known settings (not typical).
        block : bool, optional
            Wait until values are received from the device. Default True.

        Returns
        -------
        odly.PA2OutputDelay
            Output Delay settings

        Raises
        ------
        ValueError
            Invalid band
        """

        if update:
            if band == ob.BandHigh:
                target = odly.High
            elif band == ob.BandMid:
                target = odly.Mid
            elif band == ob.BandLow:
                target = odly.Low
            else:
                raise ValueError(f"Invalid band: {band}")

            self._queueCommand(
                [dr.ProtoList, f"{target}\\{dr.ProtoValues}"],
                block=block,
            )
            if block:
                self._blockingQuery()

        if band == ob.BandHigh:
            return self.outHigh.delay
        elif band == ob.BandMid:
            return self.outMid.delay
        elif band == ob.BandLow:
            return self.outLow.delay
        else:
            raise ValueError(f"Invalid band: {band}")

    # Output Mutes

    def muteOutput(
        self, band: str, channel: str, mute: bool, block: bool = True
    ) -> None:
        """Immediately mute or unmute the specified output band and channel.

        Parameters
        ----------
        band : str
            Which band to mute. Must be one of:
                dbxdriverack.BandHigh, BandMid, BandLow
        channel : str
            Which channel to mute. Must be one of:
                dbxdriverack.ChannelLeft, ChannelRight
        mute : bool
            Whether to mute (True) or unmute (False)
        block : bool, optional
            Wait until the device confirms completion. Default True.

        Raises
        ------
        ValueError
            Invalid band, channel, or mute value
        """

        if band not in [ob.BandHigh, ob.BandMid, ob.BandLow]:
            raise ValueError("Invalid band")
        if channel not in [dr.ChannelLeft, dr.ChannelRight]:
            raise ValueError("Invalid channel")
        if mute not in [True, False]:
            raise ValueError("Invalid mute value")

        if channel == dr.ChannelLeft:
            targetChannel = ob.MuteL
            if band == ob.BandHigh:
                self.muteHighLeft = mute
            elif band == ob.BandMid:
                self.muteMidLeft = mute
            elif band == ob.BandLow:
                self.muteLowLeft = mute
            else:
                raise ValueError("Invalid band")
        elif channel == dr.ChannelRight:
            targetChannel = ob.MuteR
            if band == ob.BandHigh:
                self.muteHighRight = mute
            elif band == ob.BandMid:
                self.muteMidRight = mute
            elif band == ob.BandLow:
                self.muteLowRight = mute
            else:
                raise ValueError("Invalid band")
        else:
            raise ValueError("Invalid channel")

        self._queueCommand(
            ob.CmdBuilder(
                dr.ProtoSet,
                targetChannel,
                band=band,
                value=mute,
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    def _haveAllMuteStates(self) -> bool:
        """Private function to check if all mute states are accounted for.

        Returns
        -------
        bool
            True if all mute states are present, False otherwise.
        """

        try:
            self.muteLowLeft
            self.muteLowRight
            self.muteMidLeft
            self.muteMidRight
            self.muteHighLeft
            self.muteHighRight
        except AttributeError:
            return False
        return True

    def bulkMute(
        self, action: str, updateState: bool = True, block: bool = True
    ) -> None:
        """Immediately set or poll the device for all mute states at once.

        Parameters
        ----------
        action : str
            Which action to take. Must be one of:
                dbxdriverack.CmdMuteRefresh
                    Refresh the mute states from the device
                dbxdriverack.CmdMuteRestore
                    Restore the mute states to the last known values
                dbxdriverack.CmdMuteAll
                    Mute all outputs
                dbxdriverack.CmdUnmuteAll
                    Unmute all outputs
        updateState : bool, optional
            Whether to update the local state after setting. Default True.
        block : bool, optional
            Wait until the device confirms completion. Default True.

        Raises
        ------
        ValueError
            Invalid action or band
        """

        if action not in [
            dr.CmdMuteRefresh,
            dr.CmdMuteRestore,
            dr.CmdMuteAll,
            dr.CmdUnmuteAll,
        ]:
            raise ValueError(
                "Action must be one of refresh, restore, muteall, unmuteall"
            )

        if not self._haveAllMuteStates() and not action == dr.CmdMuteRefresh:
            # Some mute are unititialized
            self.bulkMute(dr.CmdMuteRefresh)
        elif not self._haveAllMuteStates() and action == dr.CmdMuteRefresh:
            try:
                self.muteLowLeft
            except AttributeError:
                self.muteLowLeft = True
            try:
                self.muteLowRight
            except AttributeError:
                self.muteLowRight = True
            try:
                self.muteMidLeft
            except AttributeError:
                self.muteMidLeft = True
            try:
                self.muteMidRight
            except AttributeError:
                self.muteMidRight = True
            try:
                self.muteHighLeft
            except AttributeError:
                self.muteHighLeft = True
            try:
                self.muteHighRight
            except AttributeError:
                self.muteHighRight = True

        for band in [ob.BandHigh, ob.BandMid, ob.BandLow]:
            for channel in [ob.MuteL, ob.MuteR]:
                if band == ob.BandLow:
                    muteValue = (
                        self.muteLowLeft if channel == ob.MuteL else self.muteLowRight
                    )
                elif band == ob.BandMid:
                    muteValue = (
                        self.muteMidLeft if channel == ob.MuteL else self.muteMidRight
                    )
                elif band == ob.BandHigh:
                    muteValue = (
                        self.muteHighLeft if channel == ob.MuteL else self.muteHighRight
                    )
                else:
                    raise ValueError("Invalid band")

                if action == dr.CmdMuteRefresh:
                    self._queueCommand(
                        ob.CmdBuilder(
                            dr.ProtoGet,
                            channel,
                            band=band,
                        ).get(),
                        block=block,
                    )
                elif action == dr.CmdMuteRestore:
                    self._queueCommand(
                        ob.CmdBuilder(
                            dr.ProtoSet,
                            channel,
                            band=band,
                            value=muteValue,
                        ).get(),
                        block=block,
                    )
                elif action == dr.CmdMuteAll:
                    self._queueCommand(
                        ob.CmdBuilder(
                            dr.ProtoSet,
                            channel,
                            band=band,
                            value=True,
                        ).get(),
                        block=block,
                    )
                    if updateState:
                        muteValue = True
                elif action == dr.CmdUnmuteAll:
                    self._queueCommand(
                        ob.CmdBuilder(
                            dr.ProtoSet,
                            channel,
                            band=band,
                            value=False,
                        ).get(),
                        block=block,
                    )
                    if updateState:
                        muteValue = False

        if block:
            self._blockingQuery()

    def isMuted(
        self, band: str, channel: str, update: bool = True, block: bool = True
    ) -> bool:
        """Indicate whether the specified output band+channel is currently muted.

        Parameters
        ----------
        band : str
            Which band to check. Must be one of:
                dbxdriverack.BandHigh, BandMid, BandLow
        channel : str
            Which channel to check. Must be one of:
                dbxdriverack.ChannelLeft, ChannelRight
        update : bool, optional
            Query the device for the latest mute state. Default True.
            If False, just return the last known state (not typical).
        block : bool, optional
            Wait until values are received from the device. Default True.

        Returns
        -------
        bool
            True if muted, False if unmuted

        Raises
        ------
        ValueError
            Invalid band or channel
        """

        if update:
            self.bulkMute(dr.CmdMuteRefresh, block=block)

        if channel == dr.ChannelLeft:
            if band == ob.BandHigh:
                return self.muteHighLeft
            elif band == ob.BandMid:
                return self.muteMidLeft
            elif band == ob.BandLow:
                return self.muteLowLeft
            else:
                raise ValueError("Invalid band")
        elif channel == dr.ChannelRight:
            if band == ob.BandHigh:
                return self.muteHighRight
            elif band == ob.BandMid:
                return self.muteMidRight
            elif band == ob.BandLow:
                return self.muteLowRight
            else:
                raise ValueError("Invalid band")
        else:
            raise ValueError("Invalid channel")

    # RTA

    def applyRta(self, block: bool = True) -> None:
        """Apply the currently-set RTA settings to the connected PA2.

        Parameters
        ----------
        block : bool, optional
            Wait until the device confirms completion. Default True.

        Raises
        ------
        ValueError
            RTA settings not set
        """

        try:
            self.rta
        except AttributeError:
            raise ValueError("RTA settings not set")

        self._queueCommand(
            rta.CmdBuilder(
                dr.ProtoSet,
                rta.Rate,
                value=self.rta.rate,
            ).get()
        )

        self._queueCommand(
            rta.CmdBuilder(
                dr.ProtoSet,
                rta.Offset,
                value=self.rta.offset,
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    def setRta(self, rtaObj: rta.PA2Rta, apply: bool = True) -> None:
        """Sets a PA2's RTA settings to match the provided PA2Rta object.

        Parameters
        ----------
        rtaObj : rta.PA2Rta
            The RTA settings to apply
        apply : bool, optional
            Whether to apply the values to the connected device. Default True.
            If False, just update the local state only (not typical).
        """

        self.rta = rtaObj

        if apply:
            self.applyRta()

    def getRta(self, update: bool = True, block: bool = True) -> rta.PA2Rta:
        """Get the currently-connected PA2's specified RTA settings.

        Parameters
        ----------
        update : bool, optional
            Query the device for the latest RTA settings. Default True.
            If False, just return the last known settings (not typical).
        block : bool, optional
            Wait until values are received from the device. Default True.

        Returns
        -------
        rta.PA2Rta
            RTA settings
        """

        if update:
            self._queueCommand(
                rta.CmdBuilder(
                    dr.ProtoGet,
                    rta.Rate,
                ).get(),
                block=block,
            )

            self._queueCommand(
                rta.CmdBuilder(
                    dr.ProtoGet,
                    rta.Offset,
                ).get(),
                block=block,
            )

            self._blockingQuery()

        return self.rta

    # Signal Generator

    def applyGenerator(self, block: bool = True) -> None:
        """Apply the currently-set Signal Generator
        settings to the connected PA2.

        Parameters
        ----------
        block : bool, optional
            Wait until the device confirms completion. Default True.

        Raises
        ------
        ValueError
            Generator settings not set
        """

        try:
            self.generator
        except AttributeError:
            raise ValueError("Generator settings not set")

        self._queueCommand(
            gen.CmdBuilder(
                dr.ProtoSet,
                gen.Level,
                value=self.generator.level,
            ).get()
        )

        self._queueCommand(
            gen.CmdBuilder(
                dr.ProtoSet,
                gen.Mode,
                value=self.generator.mode,
            ).get(),
            block=block,
        )

        if block:
            self._blockingQuery()

    def setGenerator(self, generator: gen.PA2Generator, apply: bool = True) -> None:
        """Sets a PA2's Signal Generator settings to match
        the provided PA2Generator object.

        Parameters
        ----------
        generator : gen.PA2Generator
            The Signal Generator settings to apply
        apply : bool, optional
            Whether to apply the values to the connected device. Default True.
            If False, just update the local state only (not typical).
        """

        self.generator = generator

        if apply:
            self.applyGenerator()

    def getGenerator(self, update: bool = True, block: bool = True) -> gen.PA2Generator:
        """Get the currently-connected PA2's specified Generator settings.

        Parameters
        ----------
        update : bool, optional
            Query the device for the latest Generator settings. Default True.
            If False, just return the last known settings (not typical).
        block : bool, optional
            Wait until values are received from the device. Default True.

        Returns
        -------
        gen.PA2Generator
            Generator settings
        """

        if update:
            self._queueCommand(
                gen.CmdBuilder(
                    dr.ProtoGet,
                    gen.Level,
                ).get(),
                block=block,
            )

            self._queueCommand(
                gen.CmdBuilder(
                    dr.ProtoGet,
                    gen.Mode,
                ).get(),
                block=block,
            )

            self._blockingQuery()

        return self.generator
