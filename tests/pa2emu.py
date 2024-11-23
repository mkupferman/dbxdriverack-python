#!/usr/bin/env python3

"""
This is a feature-limited emulator for the dbx DriveRack PA2
It is intended to be used for testing the PA2 Python client library.
Only one client connection at a time is supported.
"""

import socket
import threading
import queue
import shlex
from tssplit import tssplit

import dbxdriverack as dr
import dbxdriverack.pa2 as pa2
import dbxdriverack.pa2.crossover as xo
import dbxdriverack.pa2.outputband as ob

# Constants
DeviceVersion = "1.2.0.1"
DeviceName = "Emulated PA2"

#####################################################
# TODO: create server "control" protocol to modify
# emulator state for testing various scenarios
#
num_bands = 2
mono_sub = 1
stereo_geq = True
#####################################################


class PA2Emulator:
    def __init__(self, port=19272):
        self.port = port
        self.discoverySocket = None
        self.mixerSocket = None
        self.clientSockets = []
        self.discoveryInputQueue = queue.Queue()
        self.discoveryOutputQueue = queue.Queue()
        self.mixerInputQueue = queue.Queue()
        self.mixerOutputQueue = queue.Queue()
        self.threads = queue.Queue()
        self.discoveryActive = False
        self.mixerActive = False
        self.clientAuthenticated = False

        self.testFailure = False

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.discoveryActive = False
        self.mixerActive = False
        for socket in [self.discoverySocket, self.mixerSocket] + self.clientSockets:
            if socket:
                try:
                    socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                socket.close()
                socket = None

        self._drainThreads()

    def _startThread(self, target, kwargs=None, daemon=True):
        thread = threading.Thread(target=target, kwargs=kwargs, daemon=daemon)
        thread.start()
        self.threads.put(thread)

    def _drainThreads(self):
        while not self.threads.empty():
            thread = self.threads.get()
            if thread and thread.is_alive():
                try:
                    thread.join()
                except:
                    pass

    def _listenForMixerClients(self):
        while self.mixerActive:
            try:
                client, addr = self.mixerSocket.accept()
            except:
                print("Mixer server socket failed to accept connection")
                break

            self.clientSockets.append(client)

            self._startThread(
                self._readNetworkMixer,
                kwargs={"clientSocket": client, "clientAddr": addr},
            )

            self._queueMixerResponse(client, dr.ProtoHello)

    def _readNetworkDiscovery(self):
        socket = self.discoverySocket
        queue = self.discoveryInputQueue

        while self.discoveryActive:
            try:
                data, addr = socket.recvfrom(2048)
            except:
                break

            data = data.decode("utf-8")
            for line in data.splitlines():
                queue.put((addr, line))

    def _readNetworkMixer(self, **kwargs):
        if "clientSocket" not in kwargs or "clientAddr" not in kwargs:
            raise ValueError(
                "clientSocket & clientAddr kw args required in _readNetworkMixer"
            )
        socket = kwargs["clientSocket"]
        queue = self.mixerInputQueue

        while self.mixerActive:
            try:
                data = socket.recv(2048)
            except:
                break

            data = data.decode("utf-8")
            for line in data.splitlines():
                queue.put((kwargs["clientSocket"], line))

    def _processDiscoveryInputQueue(self):
        while (
            self.discoveryActive
            or not self.discoveryActive
            and not self.discoveryInputQueue.empty()
        ):
            if not self.discoveryInputQueue.empty():
                addr, message = self.discoveryInputQueue.get()
                message = message.strip()
                command = tssplit(message, delimiter=" ")
                argc = len(command)
                if argc == 2 and command[0] == dr.ProtoGet:
                    if command[1] == pa2.ProtoModel:
                        self._queueDiscoveryResponseBundle(
                            addr,
                            [
                                (dr.ProtoGet, pa2.ProtoModel, pa2.DeviceModel),
                                (dr.ProtoGet, pa2.ProtoName, DeviceName),
                                (dr.ProtoGet, pa2.ProtoVersion, DeviceVersion),
                            ],
                        )

    def _queueMixerResponse(self, socket, *command):
        queue = self.mixerOutputQueue

        commandString = f"{command[0]}"
        if len(command) > 1:
            commandString += " " + shlex.join(command[1:])

        if queue is not None:
            queue.put((socket, commandString))

    def _queueDiscoveryResponse(self, addr, *command):
        queue = self.discoveryOutputQueue

        commandString = shlex.join(command)

        if queue is not None:
            queue.put((addr, commandString))

    def _queueDiscoveryResponseBundle(self, addr, commandList):
        commandString = ""
        for command in commandList:
            commandString += f"{command[0]} "
            commandString += " ".join(f'"{item}"' for item in command[1:])
            commandString += "\n"

        if self.discoveryOutputQueue is not None:
            self.discoveryOutputQueue.put((addr, commandString))

    def _processDiscoveryOutputQueue(self):
        while (
            self.discoveryActive
            or not self.discoveryActive
            and not self.discoveryOutputQueue.empty()
        ):
            if not self.discoveryOutputQueue.empty():
                message = self.discoveryOutputQueue.get()
                dest, message = message
                self.discoverySocket.sendto(f"{message}\n".encode("utf-8"), dest)

    def _processMixerInputQueue(self):
        while (
            self.mixerActive
            or not self.mixerActive
            and not self.mixerInputQueue.empty()
        ):
            if not self.mixerInputQueue.empty():
                socket, message = self.mixerInputQueue.get()
                message = message.strip()
                command = tssplit(message, delimiter=" ")
                argc = len(command)
                if self.clientAuthenticated:
                    if argc == 2:
                        if command[0] == dr.ProtoGet:
                            if command[1] == pa2.ProtoModel:
                                self._queueMixerResponse(
                                    socket,
                                    f"{dr.ProtoGet} {pa2.ProtoModel} {pa2.DeviceModel}",
                                )
                            elif command[1] == pa2.ProtoName:
                                self._queueMixerResponse(
                                    socket,
                                    f"{dr.ProtoGet} {pa2.ProtoName} {DeviceName}",
                                )
                            elif command[1] == pa2.ProtoVersion:
                                self._queueMixerResponse(
                                    socket,
                                    f"{dr.ProtoGet} {pa2.ProtoVersion} {DeviceVersion}",
                                )
                            elif command[1].startswith(
                                f"{ob.ProtoMutes}\\{dr.ProtoValues}"
                            ):
                                # mutes

                                if command[1].endswith(ob.MuteLowL):
                                    self._queueMixerResponse(
                                        socket,
                                        dr.ProtoGet,
                                        f"{ob.ProtoMutes}\\{dr.ProtoValues}\\{ob.MuteLowL}",
                                        ob.MuteEnabled,
                                    )
                                elif command[1].endswith(ob.MuteLowR):
                                    self._queueMixerResponse(
                                        socket,
                                        dr.ProtoGet,
                                        f"{ob.ProtoMutes}\\{dr.ProtoValues}\\{ob.MuteLowR}",
                                        ob.MuteDisabled,
                                    )
                                elif command[1].endswith(ob.MuteMidL):
                                    if self.testFailure:
                                        self.testFailure = False
                                    else:
                                        self._queueMixerResponse(
                                            socket,
                                            dr.ProtoGet,
                                            f"{ob.ProtoMutes}\\{dr.ProtoValues}\\{ob.MuteMidL}",
                                            ob.MuteEnabled,
                                        )
                                elif command[1].endswith(ob.MuteMidR):
                                    self._queueMixerResponse(
                                        socket,
                                        dr.ProtoGet,
                                        f"{ob.ProtoMutes}\\{dr.ProtoValues}\\{ob.MuteMidR}",
                                        ob.MuteDisabled,
                                    )
                                elif command[1].endswith(ob.MuteHighL):
                                    self._queueMixerResponse(
                                        socket,
                                        dr.ProtoGet,
                                        f"{ob.ProtoMutes}\\{dr.ProtoValues}\\{ob.MuteHighL}",
                                        ob.MuteEnabled,
                                    )
                                elif command[1].endswith(ob.MuteHighR):
                                    self._queueMixerResponse(
                                        socket,
                                        dr.ProtoGet,
                                        f"{ob.ProtoMutes}\\{dr.ProtoValues}\\{ob.MuteHighR}",
                                        ob.MuteDisabled,
                                    )

                        elif command[0] == dr.ProtoList:
                            if command[1].startswith(
                                f"{xo.ProtoCrossover}\\{dr.ProtoAttr}"
                            ):
                                responses = [
                                    f'{dr.ProtoList} "{xo.ProtoCrossover}\\{dr.ProtoAttr}"',
                                    "    .. : ",
                                    "    Class_Name : DriveRackCrossover",
                                    "    Instance_Name : Crossover",
                                    "    Flags : 0",
                                    "    NumSlots : 2",
                                    f"    NumBands: {num_bands}",
                                    f"    MonoSub: {mono_sub}",
                                    "    * : ",
                                    dr.ProtoListEnd,
                                ]
                                for response in responses:
                                    self._queueMixerResponse(socket, response)
                            elif command[1] == f"{pa2.Preset}":
                                responses = [
                                    f'{dr.ProtoList} "{pa2.Preset}"',
                                    "    .. : ",
                                    "    RTA : ",
                                    "    SignalGenerator : ",
                                    "    MonoMixer : ",
                                ]
                                if stereo_geq:
                                    responses.append("    StereoGEQ : ")
                                else:
                                    responses.append("    LeftGEQ : ")
                                    responses.append("    RightGEQ : ")
                                responses.extend(
                                    [
                                        "    RoomEQ : ",
                                        "    Afs : ",
                                        "    SubharmonicSynth : ",
                                        "    Compressor : ",
                                        "    Back Line Delay : ",
                                        "    Crossover : ",
                                        "    High Outputs PEQ : ",
                                        "    Low Outputs PEQ : ",
                                        "    High Outputs Limiter : ",
                                        "    Low Outputs Limiter : ",
                                        "    High Outputs Delay : ",
                                        "    Low Outputs Delay : ",
                                        "    OutputGains : ",
                                        "    OutputMeters : ",
                                        "    SV : ",
                                        "    AT : ",
                                        dr.ProtoListEnd,
                                    ]
                                )

                                for response in responses:
                                    self._queueMixerResponse(socket, response)
                else:
                    if argc == 3:
                        if command[0] == dr.ProtoConnect:
                            if (
                                command[1] == dr.AuthAdmin
                                and command[2] == dr.AuthAdminDefaultPass
                            ):
                                self.clientAuthenticated = True
                                self._queueMixerResponse(
                                    socket, f"{dr.ProtoConnectAck} {dr.AuthAdmin}"
                                )
                            else:
                                self._queueMixerResponse(
                                    socket, f"{dr.ProtoConnectFail} {command[1]}"
                                )

                print(
                    f"[MIXER] Received command: {command} from {socket.getpeername()}"
                )

    def _processMixerOutputQueue(self):
        while (
            self.mixerActive
            or not self.mixerActive
            and not self.mixerOutputQueue.empty()
        ):
            if not self.mixerOutputQueue.empty():
                message = self.mixerOutputQueue.get()
                socket, message = message
                socket.sendall(f"{message}\n".encode("utf-8"))
                print(f"[MIXER] Sent response: {message} to {socket.getpeername()}")

    def startServer(self):
        self.discoverySocket = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )
        self.discoverySocket.bind(("", self.port))
        self.discoveryActive = True
        self._startThread(self._readNetworkDiscovery)
        self._startThread(self._processDiscoveryInputQueue)
        self._startThread(self._processDiscoveryOutputQueue)
        print(f"Discovery server started on port udp/{self.port}")

        self.mixerSocket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP
        )
        self.mixerSocket.bind(("", self.port))
        self.mixerSocket.listen(1)
        self.mixerActive = True
        self._startThread(self._processMixerInputQueue)
        self._startThread(self._processMixerOutputQueue)
        self._startThread(self._listenForMixerClients)
        print(f"Mixer server started on port tcp/{self.port}")


def main():
    with PA2Emulator() as pa2emu:
        pa2emu.startServer()
        while pa2emu.discoveryActive:

            command = input("cmd> ").strip().lower()
            if command == "status":
                print("Discovery Active:", pa2emu.discoveryActive)
                print("Mixer Active:", pa2emu.mixerActive)
                print("Client Authenticated:", pa2emu.clientAuthenticated)
            elif command == "exit":
                break
                # pa2emu.discoveryActive = False
                # pa2emu.mixerActive = False
            else:
                print("Invalid command. Valid options are: status, exit")


if __name__ == "__main__":
    main()
