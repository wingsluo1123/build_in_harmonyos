# GEOS 3.12.1 adaptation notes

## Build configuration

- Build system: CMake
- Conan reference: `geos/3.12.1`
- Source: official OSGeo `geos-3.12.1.tar.bz2`
- Source SHA-256: `d6ea7e492224b51193e8244fe3ec17c4d44d0777f3c32ca4fb171140549a0d03`
- Default linkage: static
- Required language level: C++14
- Source patches: none
- CMake 4 compatibility: `CMAKE_POLICY_VERSION_MINIMUM=3.5`

The recipe uses `CMakeToolchain`; compiler paths, target flags, and the OHOS toolchain come from the Conan profile. It does not embed device-specific paths or wrapper scripts.

GEOS 3.12.1's bundled `cmake/Ccache.cmake` declares compatibility with CMake older than 3.5. CMake 4 removes that implicit compatibility mode, so the recipe sets `CMAKE_POLICY_VERSION_MINIMUM=3.5` through the generated toolchain.

## Upstream tests

`build()` enables `BUILD_TESTING` and invokes Conan's `cmake.test()`, which runs the generated CMake `test` target. GEOS 3.12.1 registers 466 upstream test entries:

| Test group | Entries | Native Windows verification |
| --- | ---: | ---: |
| C++ unit tests | 298 | 298 passed |
| XML regression tests | 168 | 168 passed |
| Total | 466 | 466 passed |

The native verification completed all 715 Ninja build steps and all 466 CTest entries. This is supplemental recipe evidence only; it is not an OHOS CI result.

## Consumer test

The Conan `test_package` finds `GEOS` through CMake, links `GEOS::geos_c`, parses WKT geometries, and verifies the reported version, a 3-4-5 distance, and polygon containment.

## Packaged interfaces

- `GEOS::geos`: C++ library target
- `GEOS::geos_c`: stable C API target with the correct dependency on `GEOS::geos`
- `geosop`: command-line geometry operations utility
- `geos-config`: package configuration helper

## Verification boundary

The authoritative OpenHarmony result is the official PR CI bound to the final commit SHA. No OHOS CI pass is claimed by this note.
