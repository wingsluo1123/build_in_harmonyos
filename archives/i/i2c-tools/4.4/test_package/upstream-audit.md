# Upstream userspace test audit

- Source: official kernel.org tag `v4.4`, commit `c20cd0b4be78e7b84104452b7fc9c570f00f92bf`.
- Release archive SHA-256: `D7BD003BB921163194C67200B027D280573EC1EAA4224B90680033683DDDFA51`.
- Tracked paths matching test/check directories or files: `0`.
- Tracked assembly sources: `0`; tracked binary artifacts: `0`.
- The root Makefile declares `.PHONY: all strip clean install uninstall`; it has no `check` or `test` target.
- `stub/i2c-stub-from-dump` is a helper for the kernel `i2c-stub` driver. It is not a userspace test suite and requires that kernel driver.
- Upstream suite result: `0/0 (100%)`, with `0` executed, `0` passed, `0` failed, `0` skipped, `0` XFAIL, and `0` broken. This is an empty upstream test inventory, not an executed test run.

The package consumer checks exercise only paths that do not require a real adapter:

- Each executable's `-V` path exits before bus handling.
- `i2cdetect -l` lists adapter metadata without scanning or opening `/dev/i2c-*`.
- Out-of-range bus values are rejected in `lookup_i2c_bus()` before `open_i2c_dev()`.
- The library checks pass descriptor `-1` to its ioctl wrapper and verify `-EBADF` error propagation.

These checks do not claim successful bus access, device scanning, adapter functionality, EEPROM reads, or SMBus/I²C transactions. Those require real hardware or an intentionally provisioned `i2c-stub` environment.
