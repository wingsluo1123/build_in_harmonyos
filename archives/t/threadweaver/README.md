# ThreadWeaver

ThreadWeaver is a KDE Frameworks 6 library that provides a job queue and job
scheduling framework on top of QThread: Queue/QueueStream job submission,
Collections and Sequences for grouped and ordered execution, job
dependencies (Dependency/DependencyPolicy), and Lambda/make_job wrappers for
plain functors. Ships `libKF6ThreadWeaver.so`. It is a QtCore-level
framework (no QWidget/GUI classes).

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- OHOS shared-library rules are SONAME-only: the recipe writes a
  `CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX` rules file defining only
  `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG` and sets
  `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`, because HMDFS rejects
  symlink(2) and the versioned `.so.6` symlink chain cannot be created (same
  policy as the other KF6 libraries).
- ECM 6.28 `KDEInstallDirs6` executes the qtbase `qtpaths` host tool at
  configure time; the recipe prepends `/system/lib64` to `LD_LIBRARY_PATH`
  so the compatible `libc++_shared.so` is resolved (the sandbox default
  contains an incompatible one under `/data/storage/el1/bundle/libs/arm64`).
- Upstream adds `examples/` to the build unconditionally (HelloWorld,
  HelloWorldRaw, HelloInternet, ThumbNailer). Every module they need
  (Qt6 Widgets/Network/Xml/Test and the uic/moc tools) ships inside the
  qtbase package in this repository, so no gating patch is required.
- The upstream autotests are QCoreApplication-level (QtTest) and run
  headless on device; all 7 CTest cases pass.

## Dependencies

- Build: ecm (extra-cmake-modules 6.28.0), CMake >= 3.29, ninja/make
- Runtime/compile: qtbase (Qt6Core)

## References

- Homepage: https://invent.kde.org/frameworks/threadweaver
- Sources: https://download.kde.org/stable/frameworks/
