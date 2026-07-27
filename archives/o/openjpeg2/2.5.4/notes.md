# openjpeg2 2.5.4 adaptation notes

## Scope

This package builds the OpenJPEG core `libopenjp2` library from the official
`v2.5.4` source archive. The first pass disables codec command-line tools, JPIP,
viewer, Java bindings, bundled third-party helpers, documentation, and upstream
tests so the OHOS package has a focused library surface.

## High-difficulty basis

Path C is appropriate because OpenJPEG has a non-trivial codec API, multiple
optional executable stacks (`opj_compress`, `opj_decompress`, `opj_dump`),
JPIP client/server code, optional image-format helper dependencies, and a large
upstream data-driven conformance/nonregression suite. The adaptation keeps the
core library first, with consumer tests covering public API use directly.

## Test coverage

Upstream `tests/CMakeLists.txt` plus `tests/unit/CMakeLists.txt` register 33
concrete tile/random-access/area/unit tests when `BUILD_TESTING=ON`,
`BUILD_CODEC=ON`, and `BUILD_UNIT_TESTS=ON`; `tests/conformance` and
`tests/nonregression` generate additional data-driven tests when their datasets
are provided. The Conan package disables these upstream tests for cross-build
packaging. The added `test_package` builds and runs one C consumer test with
six checks over version query, default parameter initialization, image creation,
component metadata, codec creation, and cleanup.

## Local validation

Local validation completed on Windows with MinGW GCC 8.1.0 and CMake 4.2.1:

- Python syntax check passed for the main recipe and test recipe.
- `git diff --check` passed.
- Placeholder/secret-marker scan over `archives/o/openjpeg2` had 0 hits.
- Official source archive SHA256 was verified:
  `a695fbe19c0165f295a8531b1e4e855cd94d0875d2f88ec4b61080677e27188a`.
- Native CMake configure/build/install of static `libopenjp2.a` passed with
  codec tools, JPIP, third-party helpers, docs, and tests disabled.
- The installed library compiled and ran `test_package/test_openjpeg2.c`
  manually with `-DOPJ_STATIC`; local consumer checks passed 6/6.

Local limitation: `conan` and Python `yaml` are not installed in this shell, so
full `conan create openjpeg2/2.5.4` and structured YAML parser validation are
pending a machine with the project Conan/OHOS environment.
