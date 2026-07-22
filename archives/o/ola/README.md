# ola — Open Lighting Architecture

OLA is an open-source framework for controlling DMX512 lighting
equipment over IP networks (Art-Net, sACN/E1.31, ESP-Net, Pathport,
ShowNet, USB-Pro, KiNet, SandNet, etc.). It provides both a C++
library (libolacommon / libola / libolaserver) and a daemon
(`olad`) that bridges IP-based lighting protocols to local DMX
hardware.

## Versions in this archive

- `0.10.9/` — initial OpenHarmony PC port (aarch64), path A scope

## Path A scope

This archive intentionally ships only the core libraries and the
`olad` daemon. The HTTP UI (web-based lighting control), Python
bindings, and individual DMX device driver plugins are **out of
scope** for the initial PR and will be ported in subsequent
commits once the core ABI is stable.

## License

OLA is dual-licensed:

- **GPL-2.0-or-later** (for the daemon and tools)
- **LGPL-2.1-or-later** (for `libolacommon`, `libola`, `libolaserver`)

Downstream consumers must comply with **both** licenses. Static
linking of the LGPL libraries into a non-LGPL application triggers
the full LGPL terms (effectively requiring either dynamic linking
or publication of the relinkable object files).