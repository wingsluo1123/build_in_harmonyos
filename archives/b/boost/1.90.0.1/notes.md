# Boost 1.90.0.1 compiled component subset

## Scope

This archive keeps upstream Boost at 1.90.0 and adds an adaptation suffix
because `boost/1.90.0` in this repository is header-only. The first compiled
subset is aimed at downstream FastNetMon 1.2.9 and includes:

- `atomic`
- `chrono`
- `program_options`
- `regex`
- `serialization`
- `thread`

## Adaptation Strategy

Boost.Build/b2 is avoided because prior OpenHarmony attempts hit the known
OHOS b2 failures in E099/E153. Boost 1.90.0 includes CMake support, so the
recipe configures CMake with `BOOST_INCLUDE_LIBRARIES` for the required
compiled components and leaves the rest of Boost header-only through the
installed include tree.

## Validation

The `test_package` builds and runs a C++ consumer that exercises:

- `boost::program_options` command line parsing
- `boost::regex` matching
- `boost::archive::text_oarchive` serialization
- `boost::thread` execution and join

Local workstation limitation: no local OHOS Conan runtime is available here, so
full `conan create boost/1.90.0.1` is pending remote OHOS CI.
