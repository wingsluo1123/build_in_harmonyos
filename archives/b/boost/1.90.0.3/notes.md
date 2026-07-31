# Boost 1.90.0.3 compiled component subset

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

For OHOS cross builds, the recipe generates a small `clang++` wrapper for b2.
Boost.Build's generic `clang-linux` toolset can append a Linux target triple
after Conan's OHOS target flags; the wrapper filters that generic target and
executes the configured OHOS compiler with the recipe's OHOS target triple.

Boost 1.90.0's Serialization test Jamfile names the Filesystem directory
project as a library requirement. The actual library target is
`/boost/filesystem//boost_filesystem`, so the test-only patch names that target
explicitly. It changes no production source or runtime behavior and lets the
upstream Serialization tests link the dependency they already declare.

Some upstream Regex examples cast `istream::in_avail()` directly to a string
capacity. File-backed stream buffers may report a negative availability, which
turns into an enormous unsigned allocation request. The second test-only patch
reserves only a positive value in each affected example; it preserves normal
input processing and does not affect the Regex library implementation.

## Validation

The `test_package` builds and runs a C++ consumer that exercises:

- `boost::program_options` command line parsing
- `boost::regex` matching
- `boost::archive::text_oarchive` serialization
- `boost::thread` execution and join

On 2026-07-31, a clean WSL/Linux x86_64 GCC 15.2.0
`conan create archives/b/boost/1.90.0.3 --build=boost/1.90.0.3` completed
successfully. The recipe ran all selected component upstream Boost.Build test
trees: 1578/1578 targets passed, with 76 upstream expected compile-failure
assertions accepted by Boost.Build and no unexpected failures. The Conan
consumer test then built, linked and ran successfully (1/1).

This is local Linux evidence, not an OpenHarmony target-runtime claim.
Cross-built OpenHarmony binaries still require execution on a runnable target
before platform-runtime acceptance or CI rebuild is requested.
