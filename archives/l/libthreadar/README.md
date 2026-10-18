# libthreadar

libthreadar is a C++ library that provides thread, mutex, semaphore, barrier, condition, and related synchronization classes.

## HarmonyOS adaptation

The 1.6.1 recipe probes for `pthread_cancel` and uses libthreadar's cooperative cancellation method when the function is unavailable. The header install rule is patched to preserve relative includes between co-located public headers, keeping Conan package headers relocatable.

## Dependencies

The library has no runtime Conan dependencies. Building from the release source requires Autoconf, Automake, GNU Libtool, and M4; the pinned build-tool versions are declared in the version recipe.

## References

- Upstream repository: <https://github.com/Edrusb/libthreadar>
- Upstream tag: `v1.6.1`
