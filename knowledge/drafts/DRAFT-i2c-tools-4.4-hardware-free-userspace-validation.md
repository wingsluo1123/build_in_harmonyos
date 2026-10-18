# Hardware-free validation for Linux I²C userspace packages

## Problem

An I²C utility can compile successfully on a device that has no physical adapter. That build does not establish that scanning, address selection, SMBus operations, EEPROM reads, or any kernel-driver interaction works. Those paths open `/dev/i2c-*` and issue Linux I²C ioctls.

For i2c-tools v4.4, the upstream release has no test source files and no `check` or `test` target. Its `i2c-stub-from-dump` helper configures a kernel test driver; it is not a userspace test suite and is not usable when that driver is unavailable. Record this as an upstream test inventory of zero, not as an executed test suite.

## Reusable method

1. Audit the exact source tag, not a later branch: inspect its build targets and search its tracked tree for test/check files. State the upstream count and command separately from package tests.
2. Select deterministic command paths that do not open an adapter. Version output exits before bus handling; `i2cdetect -l` lists adapter metadata without scanning; an out-of-range bus number is rejected by argument parsing before device open.
3. Build a real consumer of the installed library. On an invalid file descriptor, the kernel ioctl fails with `EBADF`; the public library returns `-errno`. This checks header installation, link metadata, and error propagation without pretending to exercise a bus.
4. Keep adapter transactions outside the hardware-free count. Run those only with a real adapter or a deliberately provisioned `i2c-stub`, and report that setup separately.

For the v4.4 package, the consumer suite comprises five `-V` checks, one `i2cdetect -l` check, two invalid-bus parser checks, and three `libi2c` invalid-descriptor checks. Each check is counted once; none opens `/dev/i2c-*` or sends an I²C transaction.

## Evidence and limits

- `Makefile`: only `all`, `strip`, `clean`, `install`, and `uninstall` are declared; there is no upstream test target.
- `tools/i2cbusses.c`: bus numbers above `0xFFFFF` are rejected before `open_i2c_dev`.
- `tools/i2cdetect.c`: `-V` and `-l` are handled before the bus scan path.
- `lib/smbus.c`: a failed `ioctl` is returned as `-errno`.
- `stub/i2c-stub-from-dump`: uses the kernel `i2c-stub` driver, so it is not a userspace-only test.

These checks do not validate real adapter discovery, functionality ioctls, device permissions, bus timing, electrical behavior, address responses, or successful reads and writes. Do not infer physical hardware support from a passing build or from these checks.

## Independent pattern

The separate `smbus2` project demonstrates another safe testing technique: its `tests/test_smbus2.py` replaces `os.open`, `os.close`, and `ioctl` with mocks for protocol-level unit tests. Such mock tests do not count as i2c-tools upstream tests and do not establish kernel or adapter behavior. The local Windows runner cannot import that Linux-specific module because Python has no `fcntl`; this corpus example is source evidence only, not a reported passing run.
