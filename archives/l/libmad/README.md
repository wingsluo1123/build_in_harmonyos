# libmad

## Description

libmad (MAD) is a high-quality MPEG audio decoder library. It supports
MPEG-1, MPEG-2 (Low Sampling Frequencies extension), and MPEG 2.5 formats.
All three audio layers (Layer I, II, and III / MP3) are fully implemented.

Key features:
- 24-bit PCM output
- 100% fixed-point (integer) computation
- New implementation based on ISO/IEC standards
- Distributed under GPL-2.0-or-later

This is the Tenacity Team fork (0.16.4) which migrated from autotools to CMake.

- Homepage: https://codeberg.org/tenacityteam/libmad
- License: GPL-2.0-or-later
- Language: C

## OHOS Adaptation

- Build system: CMake
- Current version: 0.16.4
- Platform: aarch64 (OHOS)
- Built as shared library (libmad.so)
- ASO (assembly optimization) disabled for cross-compile safety
- No patches required
- See 0.16.4/notes.md for details

## Dependencies

- **Required**: None
- **Optional**: None

## Library Outputs

- lib/libmad.so - shared library
- include/mad.h - public header (generated)
- lib/pkgconfig/mad.pc - pkg-config file
- CMake config: madConfig.cmake (namespace: mad::)
