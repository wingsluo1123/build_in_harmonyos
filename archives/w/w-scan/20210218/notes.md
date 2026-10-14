# w_scan 20210218 adaptation notes

## Upstream information

- Software: w_scan, a command-line DVB channel scanner.
- Source: `https://deb.debian.org/debian/pool/main/w/w-scan/w-scan_20210218.orig.tar.bz2`.
- SHA256: `75d7447ebeddfb9ce251f32a93f23190ed46dca44f5b701f2af11e1787b9eb08`.
- License: GPL-2.0-or-later; the archive includes `COPYING`.
- The upstream archive has no automated test suite and no `check` target.

## Build approach

The archive contains generated Autotools files. The upstream `version` target rewrites `version.h` and `configure.ac` and calls `autoconf` when it runs. The recipe instead compiles the same 20 C translation units listed in `Makefile.am` directly with the Conan-provided C compiler. The build uses `-D_GNU_SOURCE`, PIE, RELRO, and `-z now`; it does not depend on a host Autotools installation.

The upstream `emulate.c` uses CRLF line endings. A normal LF patch does not apply cleanly, so the recipe performs a strict, CRLF-preserving replacement of the non-portable `<sys/errno.h>` include with standard `<errno.h>`. The DVB UAPI headers are supplied by the OHOS sysroot, and the libc supplies `iconv` and `clock_gettime`, so this version has no Conan dependencies.
The OHOS clang sysroot also does not expose `time_t` transitively from the DVB headers used by `descriptors.h`. The recipe adds the standard `<time.h>` include explicitly so the same source set compiles on OHOS without depending on a Linux libc include chain.

## Verification

A Linux Clang 18 preflight build completed successfully, and the local CLI probe reported version `20210218`, basic and extended help, country and satellite listings, and rejection of an unknown option. That is a source-level preflight only, not an OHOS runtime result.

The test package runs six deterministic, hardware-independent checks against the packaged executable. A real DVB scan is deliberately not part of the test because it requires a frontend device and tuning data.

## CI status

The manifest and package metadata are marked `pending_ci`. After GitCode CI completes, replace the pending status with the actual OHOS build and test result rather than treating the Linux preflight as target evidence.
