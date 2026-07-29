# libsndfile

libsndfile is a C library for reading and writing sampled audio files. The
HarmonyOS Conan recipe uses the upstream CMake build and produces a static
library.

## Package scope

The 1.2.2 recipe disables external FLAC, Vorbis, Ogg, Opus, and MPEG codecs so
that the package remains reproducible with the dependencies currently
available in the OpenHarmony Conan repository. It also disables upstream
command-line programs; consumers receive the library, public headers,
pkg-config metadata, and CMake package metadata.

## Conan usage

```cmake
find_package(SndFile CONFIG REQUIRED)
target_link_libraries(my_target PRIVATE SndFile::sndfile)
```

## References

- Homepage: https://libsndfile.github.io/libsndfile/
- Source: https://github.com/libsndfile/libsndfile
- API documentation: https://libsndfile.github.io/libsndfile/api.html
