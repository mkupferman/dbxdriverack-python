# DBX DriveRack client for Python

This module provides a Python client library for discovering, connecting to,
reading values from, and controlling aspects of a dbx DriveRack&reg;
loudspeaker management system device.

Presently, only the DriveRack PA2 model is supported.

## Requirements

* Python (>= 3.11)

  * Other dependencies are specified within the project files
    for automatic installation by a package manager, such as pip.

* A compatible DriveRack hardware unit:

  * DriveRack PA2 (firmware version 1.2.0.1)

* Network connectivity between this client and the device.

  * Both must be on the same IPv4 subnet for discovery to work.

## Getting started

### Install

```shell
pip install dbxdriverack
```

### Discover online DriveRack devices

```python
import dbxdriverack.pa2 as pa2

with pa2.PA2() as drack:
    devices = drack.discoverDevices()

    print(devices)
```

### Connect and mute all outputs

```python
import dbxdriverack.pa2 as pa2

with pa2.PA2() as drack:
    address = "192.168.1.100"  # or use discovery to find
    drack.connect(address)

    drack.bulkMute(dr.CmdMuteAll)
```

### Examples

See the docs/examples/ directory for examples of each DriveRack feature.

## Documentation

Module documentation, including functions and constants, is
[available here](https://mkupferman.github.io/dbxdriverack-python/).

## Limitations

At this time, only the DriveRack PA2 is supported. I simply do not own any
other models, such as the VENU360, to develop and test with.

This is intended to be used for one-shot or bulk automated operations on
a DriveRack, for example, getting or changing particular settings at a
point in time. It is not designed to be connected to a device long-term
and used interactively. While the DriveRack (and its native clients) *do*
support realtime parameter change tracking via subscriptions, this module
does not (and does not plan to) support these subscriptions.
Furthermore, the default timeout values in this module may make even
issuing commands manually in an interactive Python session difficult.

## Contributing

Any DriveRack PA2 users are encouraged to test this module and provide
bug reports or code contributions. I am seeking anyone with other
DriveRack models (such as the VENU360) to help develop support for
this and other devices.

## Acknowledgements

dbx, DriveRack&reg;, and other brand names are trademarks of
Harman International Industries, Inc., a subsidiary of
Samsung Electronics Co., Ltd.

This project is not affiliated with or endorsed by any of these companies,
and the use of their trademarks is for identification purposes only.
