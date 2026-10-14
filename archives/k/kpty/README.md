# KPty

KPty is a KDE Frameworks 6 library implementing pty (pseudo terminal)
support: `KPty` (master/slave pty pair, controlling tty, terminal
attributes), `KPtyDevice` (QIODevice wrapper around the pty master) and
`KPtyProcess` (QProcess subclass running a child on a pty). Ships
`libKF6Pty.so`.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `UTEMPTER` is optional upstream (`find_package(UTEMPTER)`): the OHOS
  sysroot does not provide it, so the utmp bookkeeping path falls back to the
  utmp/utmpx calls OHOS libc does not implement — patch 0002 handles those with
  neutral symbol probes; the OHOS port still needs the two patches under
  `6.26.0/patches/` (CMake UNIX detection + utmp symbol probes). The pty device itself is provided
  by the OHOS libc — `openpty`/`forkpty` are exported by `libc.so` and
  `pty.h` is present in the sysroot.
- `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG` injected for `os=OHOS`: native
  device builds stay in CMake's Generic platform module (no
  `CMAKE_SYSTEM_NAME`), which has no `-Wl,-soname` rule, so `libKF6Pty.so`
  would otherwise be packaged without `DT_SONAME` (kcodecs 6.26.0 precedent,
  knowledge entry E330).
- `ECM_MODULE_PATH` is set manually: the CMakeDeps-generated
  `ECMConfig.cmake` does not propagate the variable that KF6 projects rely on
  to find `KDEInstallDirs`/`KDECMakeSettings`.
- `conan_cmakedeps_paths.cmake` is generated manually because `qtbase` uses
  `cmake_find_mode=none`, which prevents CMakeDeps from putting its
  `lib/cmake` directory on `CMAKE_PREFIX_PATH`.
- `/system/lib64` is prepended to `LD_LIBRARY_PATH` for the configure and test
  runs: the sandbox `LD_LIBRARY_PATH` carries an incompatible
  `libc++_shared.so`, which would otherwise shadow the compatible one used by
  the qtbase `qtpaths` host tool that ECM 6.26 `KDEInstallDirs6` executes
  (kconfig 6.26.0 / bluez-qt 6.28.0 precedent).
- Upstream tests: `BUILD_TESTING=ON` builds the upstream autotest
  `autotests/kptyprocesstest.cpp` (`KPtyProcessTest`, a QTest with 5 slots)
  and the recipe runs it through `ctest` inside `build()`. The pty syscalls
  needed by the suite come from the OHOS libc, so the suite is runnable on
  device in a headless session.

## Dependencies

- Build: ecm (extra-cmake-modules)
- Runtime/compile: qtbase (Qt6Core, Qt6Test), kcoreaddons, ki18n

## References

- Homepage: https://invent.kde.org/frameworks/kpty
- Sources: https://download.kde.org/stable/frameworks/
