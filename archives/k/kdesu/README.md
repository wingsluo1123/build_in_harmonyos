# KDESu

KDESu is a KDE Frameworks 6 library for privilege escalation. It ships
`libKF6Su.so` (`KDESu::SuProcess`, `KDESu::SshProcess`, `KDESu::StubProcess`,
`KDESu::Client`) plus two internal helpers: `kdesud` (password-caching daemon)
and `kdesu_stub` (the helper the library execs through su/sudo/doas). This
package does not provide a user-facing command-line tool.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `X11` is optional upstream (`find_package(X11)`): the OHOS sysroot does not
  provide it, so `HAVE_X11=0` and the Xauthority/X11-only code paths compile
  out. No source patches are needed for this package.
- `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG` is injected for `os=OHOS`:
  native device builds stay in CMake's Generic platform module, which has no
  `-Wl,-soname` rule (kcodecs 6.26.0 precedent, knowledge entry E330). The
  device profile's `no-versioned-soname` user_toolchain (symlinks under
  `/storage` are denied) then produces the platform-standard single
  unversioned `libKF6Su.so`, which carries `DT_SONAME=libKF6Su.so`.
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
  (kconfig/kpty 6.26.0 precedent).
- `kdesud` and `kdesu_stub` install into `KDE_INSTALL_LIBEXECDIR_KF`, which
  resolves to `<prefix>/bin/kf6/` on this platform. They are internal helpers
  of the library, not user commands, so the package remains a pure library
  (no `commands.json`, R38/L0k).
- Upstream tests: `BUILD_TESTING=ON` builds and runs both suites through
  `ctest` inside `build()`. `kdesudtest` (lexer round-trip) passes.
  `kdesutest` cannot run in the device sandbox: pty allocation is denied
  (`kf.pty: Can't open a pseudo teletype`) before su/sudo is ever spawned,
  and the device has no `su`/`sudo`/`doas` binaries nor a passwd entry for the
  sandbox uid. Per R51 the measured result is declared verbatim in
  `6.26.0/notes.md` and `6.26.0/test_package/MANIFEST.yml` rather than
  reported as a pass; API-level coverage is provided by `test_package/`,
  which also executes the installed `kdesu_stub` and completes its `stop`
  installation check.
