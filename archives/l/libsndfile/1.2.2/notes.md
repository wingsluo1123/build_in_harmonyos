# libsndfile 1.2.2 adaptation notes

## Build configuration

- Build system: CMake
- Status: built
- Library type: static
- External codecs: disabled
- Command-line programs and examples: disabled
- CMake 4 compatibility: `CMAKE_POLICY_VERSION_MINIMUM=3.5`

The recipe uses CMake to avoid the Autotools temporary-file behavior that is
not reliable on HMDFS. It does not hard-code compiler paths, SDK paths, install
prefixes, or user directories; Conan's CMake toolchain supplies those values.

## Dependency boundary

`ENABLE_EXTERNAL_LIBS=OFF` and `ENABLE_MPEG=OFF` keep the recipe independent of
unpublished FLAC, Vorbis, Ogg, Opus, mpg123, and LAME packages. The resulting
library supports the formats implemented directly by libsndfile, including
WAV and AIFF, but not the disabled optional codecs.

The two existing `config.guess` and `config.sub` patches are legacy Autotools
assets and are intentionally not declared by this CMake recipe.

## Verification

The Conan `test_package` links to `SndFile::sndfile`, calls
`sf_version_string()`, and validates a WAV/PCM format with
`sf_format_check()`. This is a real consumer API test and fails if the package
headers or static library are unavailable.
