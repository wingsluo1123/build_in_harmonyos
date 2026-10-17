# Experimental native thermal backend

This build is a partial xmbmon 2.05 adaptation. It retains both the upstream
mbmon CLI and xmbmon X11/Xt program. Native temperature readings come from
OpenHarmony's installed thermal service; labels come from that service.
The original raw x86 motherboard backend remains available through CMake's
`MBMON_BACKEND=legacy` choice, outside this OHOS-specific Conan recipe.

On the tested OHOS 6.1.0.115 device, `TEMP0`, `TEMP1`, `TEMP2` are `system_h`,
`Battery`, and `shell_frame`. They are not renamed CPU/motherboard/chipset.
The service values are millidegrees Celsius. `mbmon -T 7 -c 1` reads all three;
`-f` converts to Fahrenheit. `mbmon -T 7 -P PORT -b` serves temperature output
over TCP in the foreground. Use a private test port and terminate the owned
server process when finished. The original daemon form remains available.

RPM and motherboard voltage rails remain outside this backend's supported
physical quantities. They display N/A; finite CLI runs requesting them exit 3.
The separate `mbmon --fan-raw SNAPSHOT [COUNT [SECONDS]]` reads two real fan
channels collected by the installed `share/xmbmon/collect_fans_hdc.py` host
helper. The helper invokes HDC ThermalService dump, preserves source output,
and atomically publishes a timestamped record into the task's shared directory.
Values keep `unit=raw`; no undocumented RPM conversion is applied. HDC must
remain connected while collecting. HiShell itself has no proven direct access
to this dump interface. A sample older than five seconds, missing or malformed
record returns N/A and exit 3. This is a host-assisted mode, not standalone fan
monitoring. Voltage work was excluded from this iteration by the user.
Original direct ISA/SMBus/chip selection flags return a clear error here.
The GUI leaves missing values out of graph segments and displays N/A.

The shared bridge has a C interface and privately uses the platform C++ ABI
(`std::__h` and system `libc++.so`). It links thermal/IPC/utils libraries from
`/system/lib64/platformsdk`. This is an internal, version-sensitive service
interface, not a public NDK compatibility promise. The 19 required upstream
headers have pinned source URLs and SHA256 in PROVENANCE.json, with original
Apache-2.0 notices. The unused ability_info.h include was removed; line endings
and final newlines were normalized. No platform library binary is redistributed.

The tested toolchain is native HNP SDK 26.0.0.18 / Clang 15. The frontend code
does not carry C++ library objects across the bridge. Runtime paths are set at
link time so CMake install preserves the ELF bytes and signature. Use Conan's
run environment for the X11 dependency libraries. No setuid installation is
used for the service backend.

Graphical operation requires an X server and DISPLAY. An unconfigured launch
reports a missing display. The separate deployment bundle now runs the official
OHOS aarch64 Xvfb, the native xmbmon binary and a loopback HTTP framebuffer
viewer on the same HarmonyOS device. The device browser displays real pixels
and supports two resize controls. Native mapping, timer repaint, resize and
expose checks passed, with real browser screenshots. This is an on-device
X11/browser display path, not an ArkUI window or a generic remote desktop.
Xvfb runtime dependencies, upstream libxkbfile, PNG shared-library linking and
the process-local installation-path adapter belong to that separate bundle.
They are not silently added to the xmbmon Conan dependency graph.
The earlier host-Xvfb experiment is retained only as historical evidence.
Out-of-range curves
are limited to the plot area; numeric labels retain the actual temperatures.
Zero-width temperature or voltage ranges are rejected before plotting.
`test_package` retains `full_adaptation: false`: its 22 checks validate the
partial temperature implementation. Nine additional parser fixtures validate
fan record handling; three live fan samples and the actual stale-snapshot case
are recorded separately. GUI integration checks are also separate. These
results do not claim complete motherboard monitoring or a contest success state.
