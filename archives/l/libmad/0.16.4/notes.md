# libmad 0.16.4 adaptation notes

## Status

Built as shared library for OHOS aarch64 on 2026-08-05.

## Build Approach

- Source: Debian pool orig tarball libmad_0.16.4.orig.tar.xz (Tenacity Team fork).
- Upstream build system: CMake (not autotools - the Tenacity Team fork migrated to CMake).
- Recipe strategy: build shared library (BUILD_SHARED_LIBS=ON).
- ASO (architecture-specific optimizations) disabled for cross-compile safety.
- Example application build disabled (not needed for library package).
- No external dependencies; standalone C library.

## Source Handling

No patches applied. The CMake build system handles OHOS platform detection
via CMAKE_SYSTEM_NAME=HarmonyOS (set automatically by the OHOS-adapted Conan).

## Build Configuration

- BUILD_SHARED_LIBS=ON - shared library (libmad.so)
- ASO=OFF - disabled ARM assembly optimization (imdct_l_arm.S) for cross-compile
- EXAMPLE=OFF - no example binary
- On aarch64: FPM_64BIT auto-selected (64-bit fixed-point math)
- Header mad.h generated from mad.h.in via CMake configure_file()

## Library Output

- Library: libmad.so (shared)
- Header: mad.h
- pkg-config: mad.pc
- CMake config: madConfig.cmake with namespace mad::

## Consumer Test

The Conan test_package builds a C consumer against mad::mad.
It initializes a mad_decoder, runs it in sync mode (immediately stops via
input callback returning MAD_FLOW_STOP), finishes the decoder, and verifies
the version string contains 0.16.
