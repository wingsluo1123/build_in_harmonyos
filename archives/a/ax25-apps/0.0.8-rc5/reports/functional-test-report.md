# Functional Test Report — ax25-apps 0.0.8-rc5

**Date**: 2026-07-17
**Platform**: HarmonyOS PC (aarch64-linux-ohos)
**Compiler**: clang 15.0.4

## Build Environment

- Source: ax25-apps_0.0.8-rc5+git20230513+afc4a5f.orig.tar.xz
- SHA256: dc32cf12d05ee516adefefdf81293ed2be6d79f2137155ae6bccdf2fde7029a9
- Build system: autotools (configure.ac + Makefile.am)
- Dependencies: libax25/0.0.12-rc5 (static), ncursesw, libiconv

## Installed Binaries

| Binary | Location | Type |
|--------|----------|------|
| call | bin/ | User tool |
| listen | bin/ | User tool |
| ax25ipd | sbin/ | System daemon |
| ax25rtd | sbin/ | System daemon |
| ax25rtctl | sbin/ | Control utility |
| ax25mond | sbin/ | Monitor daemon |

## ELF Architecture Verification

All 6 binaries verified as ELF64 AArch64:

```
--- ax25ipd ---
  Class:                             ELF64
  Machine:                           AArch64
--- ax25rtd ---
  Class:                             ELF64
  Machine:                           AArch64
--- ax25rtctl ---
  Class:                             ELF64
  Machine:                           AArch64
--- ax25mond ---
  Class:                             ELF64
  Machine:                           AArch64
--- call ---
  Class:                             ELF64
  Machine:                           AArch64
--- listen ---
  Class:                             ELF64
  Machine:                           AArch64
```

## ELF Dependency Analysis (readelf -d)

| Binary | NEEDED libraries |
|--------|-------------------|
| call | libiconv.so.2, libc.so |
| listen | libc.so |
| ax25ipd | libc.so |
| ax25rtd | libc.so |
| ax25rtctl | libc.so |
| ax25mond | libc.so |

Note: libax25 and libncursesw are statically linked (libax25 shared=False).

## Functional Test Results

### 1. call --help
**Exit code**: 1
**Output**:
```
/storage/Users/currentUser/test-install-ax25-apps-0.0.8-rc5/storage/Users/currentUser/usr/local/bin/call: unrecognized option: -
usage: call [-8] [-b l|e] [-d] [-h] [-i] [-m s|e] [-p paclen] [-r] [-R]
            [-s mycall] [-S] [-t] [-T timeout] [-v] [-w window] [-W]
            port callsign [[via] digipeaters...]
```
**Note**: call doesn't support --help flag, but shows usage on unrecognized option.

### 2. listen --help
**Exit code**: 1
**Output**:
```
/storage/Users/currentUser/test-install-ax25-apps-0.0.8-rc5/storage/Users/currentUser/usr/local/bin/listen: unrecognized option: -
Usage: listen [-8] [-a] [-c] [-h] [-i] [-p port] [-r] [-t..] [-v]
```
**Note**: listen doesn't support --help flag, but shows usage on unrecognized option.

### 3. ax25ipd --help
**Exit code**: 0
**Output**:
```
ax25ipd 0.0.8-rc5
Copyright 1991, Michael Westerhof, Sun Microsystems, Inc.
This software may be freely used, distributed, or modified, providing
this header is not removed

Usage:
/storage/Users/currentUser/test-install-ax25-apps-0.0.8-rc5/storage/Users/currentUser/usr/local/sbin/ax25ipd [flags]

Flags:
  --version, -v                 Print version of program
  --help, -h                    This help screen
  --loglevel NUM, -l NUM        Set logging level to NUM
  --configfile FILE, -c FILE    Set configuration file to FILE
  --ttydevice TTYDEV, -d TTYDEV Set device parameter to TTYDEV
  --nofork, -f                  Do not put daemon in background
```

### 4. ax25ipd --version
**Exit code**: 0
**Output**:
```
ax25ipd 0.0.8-rc5
Copyright 1991, Michael Westerhopf, Sun Microsystems, Inc.
This software may be freely used, distributed, or modified, providing
this header is not removed
```

### 5. ax25rtd --help
**Exit code**: 1
**Output**:
```
axconfig: SIOCGIFHWADDR: No such device
ax25rtd: no AX.25 port configured
```
**Note**: ax25rtd tries to configure AX.25 ports at startup. Expected behavior on system without AX.25 hardware.

### 6. ax25rtctl --help
**Exit code**: 1
**Output**:
```
usage:
ax25rtctl -a|--add ax25 <callsign> <dev> <time> [digipeater]
          -a|--add ip <ip> <dev> <time> <call> <ipmode>
          -d|--del ax25 <callsign> <dev>
          -d|--del ip <ip>
          -l|--list ax25|ip
          -e|--expire <minutes>
          -s|--save
          -r|--reload
          -q|--shutdown
          -V|--Version
          -h|--help
          -v|--version
```

### 7. ax25rtctl --version
**Exit code**: 0
**Output**:
```
ax25rtctl: 0.0.8-rc5
```

### 8. ax25rtctl -V
**Exit code**: 1
**Output**:
```
ax25rtctl version 0.0.8-rc5
ax25rtctl connect: No such file or directory
```
**Note**: Shows version then tries to connect to ax25rtd socket (expected to fail without ax25rtd running).

### 9. ax25mond --help
**Exit code**: 0
**Output**:
```
Usage: /storage/Users/currentUser/test-install-ax25-apps-0.0.8-rc5/storage/Users/currentUser/usr/local/sbin/ax25mond [-v|--version]
```

### 10. ax25mond --version
**Exit code**: 1
**Output**:
```
/storage/Users/currentUser/test-install-ax25-apps-0.0.8-rc5/storage/Users/currentUser/usr/local/sbin/ax25mond: Version 0.0.8-rc5

Copyright (C) 1998-1999 Johann Hanne, DH3MB. All rights reserved.
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
```

## make check

```
Making check in ax25ipd
make[1]: Nothing to be done for 'check'.
Making check in ax25rtd
make[1]: Nothing to be done for 'check'.
Making check in call
make[1]: Nothing to be done for 'check'.
Making check in listen
make[1]: Nothing to be done for 'check'.
Making check in ax25mond
make[1]: Nothing to be done for 'check'.
```

**Note**: No upstream test suite defined. All modules pass `make check` with no test targets.

## Summary

- All 6 binaries compiled successfully for aarch64-linux-ohos
- All binaries verified as ELF64 AArch64
- libax25 statically linked (no runtime dependency on libax25)
- call binary has runtime dependency on libiconv.so.2
- All other binaries depend only on libc.so
- Functional tests confirm binaries are operational (show version/usage info)
- make check: No test suite (expected for this type of software)
