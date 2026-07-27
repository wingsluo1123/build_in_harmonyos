# Test Report — aws-c-io 0.27.5

## Build Summary
- **Package**: aws-c-io/0.27.5@ohpcd/stable
- **Platform**: HarmonyOS (aarch64) 
- **Build System**: CMake
- **Build Type**: Release (shared library)
- **Result**: ✅ SUCCESS

## Build Output
- `libaws-c-io.so` — shared library
- 25 header files installed
- CMake config files: aws-c-io-config.cmake, aws-c-io-targets.cmake, aws-c-io-targets-release.cmake

## Dependencies
- aws-c-common/0.14.3@ohpcd/stable
- aws-c-cal/0.9.15@ohpcd/stable
- aws-lc/5.4.0 (transitive, provides libcrypto)

## Patches Applied
1. `0001-CMakeLists-add-harmonyos-platform.patch` — Adds HarmonyOS to CMakeLists.txt platform detection (Linux/Android branch)
2. `0002-CMakeLists-add-threads-before-cal.patch` — Adds `find_package(Threads REQUIRED)` before `find_package(aws-c-cal)` so `Threads::Threads` target exists when aws-lc's crypto-config.cmake references it

## Test Package Results
- L0 (test binary run): ✅ PASS — aws_io_library_init/clean_up executed successfully
- L1 (CTest): ✅ PASS — 1/1 test passed (test_aws_c_io)
- G2 (conan create clean build): ✅ PASS
- G3 (system library isolation): ✅ PASS
- G4 (artifact integrity): ✅ PASS

## Conan Verify
All gates (G0, G1, G2, G3, G4) passed.
