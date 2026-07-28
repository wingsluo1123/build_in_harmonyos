# Boost 1.90.0.1 compiled component subset

## Scope

This archive keeps upstream Boost at 1.90.0 and adds an adaptation suffix
because `boost/1.90.0` in this repository is header-only. The first compiled
subset is aimed at downstream FastNetMon 1.2.9 and includes:

- `atomic`
- `chrono`
- `filesystem`
- `program_options`
- `regex`
- `serialization`
- `thread`
- `timer`

## Adaptation Strategy

This recipe uses Boost.Build/b2 directly because the compiled components need
Boost's native build metadata. The recipe limits b2 to the component subset
above, sets a deterministic `--layout=system`, and preserves the rest of Boost
as headers through the installed include tree.

## Validation

The `test_package` builds and runs a C++ consumer that exercises:

- `boost::program_options` command line parsing
- `boost::regex` matching
- `boost::archive::text_oarchive` serialization
- `boost::thread` execution and join

Local workstation limitation: no local OHOS Conan runtime is available here, so
full `conan create boost/1.90.0.1` is pending remote OHOS CI.
