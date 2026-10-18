# kwindowsystem 6.28.0 notes

## Scope

This package is part of the KF6 6.28.0 chain refresh. It updates the
published 6.26.0.1 HarmonyOS PC recipe to KDE Frameworks 6.28.0. The
6.26.0.1 recipe is used as the base recipe; its DT_SONAME injection is
replaced by the device-verified symlink-free soname pattern (see below).

## Upstream changes 6.26.0.1 -> 6.28.0 (relevant to the OHOS adaptation)

- The top-level `CMakeLists.txt` changed only two lines: `KF_VERSION`
  `6.26.0 -> 6.28.0` and `find_package(ECM 6.26.0 -> 6.28.0 NO_MODULE)`.
  The recipe's `tool_requires` moves accordingly (ecm/6.26.0 ->
  ecm/6.28.0); nothing else in the configure inputs changed.
- The OHOS CMake patch applies to the 6.28.0 tree verbatim: both hunks
  (`include(ECMQmlModule)` at line 29 and `ecm_install_po_files_as_qm(poqm)`
  at line 89) land at the same context lines with zero fuzz, because the
  lines around them are untouched.
- `src/CMakeLists.txt`: the logging-category declarations dropped their
  `DEFAULT_SEVERITY Warning` lines and `DEPRECATION_VERSIONS` gained `6.28`
  - no OHOS build impact.
- `src/kkeyserver.h`: `KWINDOWSYSTEM_EXPORT` / 
  `KWINDOWSYSTEM_DEPRECATED_VERSION(6, 0, ...)` attribute order swapped on
  two legacy X11 key-symbol helpers - no build impact, and these helpers are
  behind the X11 guard anyway.
- The remaining changes (`kwaylandextras`, the Wayland platform plugin, the
  xcb `netwm` backend, `tests/kwaylandextrastest.cpp`, translations) are in
  components disabled on OHOS (`KWINDOWSYSTEM_X11=OFF`/
  `KWINDOWSYSTEM_WAYLAND=OFF`, qm generation off) or are test-side only.
- Requirements are unchanged: Qt >= 6.9.0 (`Qt6Gui` plus `Qt6GuiPrivate`
  guarded by the >= 6.10.0 version check on this Qt version) satisfied by
  qtbase/6.11.1; the option set (`KWINDOWSYSTEM_X11` / `KWINDOWSYSTEM_WAYLAND`
  / `KWINDOWSYSTEM_QML`) is unchanged, so the OHOS baseline keeps all three
  off and the dummy backend keeps the symbols (WIN32/APPLE/ANDROID/HAIKU
  auto-disable X11/Wayland upstream, which validates this path).

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KWINDOWSYSTEM_QML=OFF` disables optional QML bindings.
- `KWINDOWSYSTEM_X11=OFF` and `KWINDOWSYSTEM_WAYLAND=OFF` avoid unavailable
  X11/Wayland stacks on OHOS; the dummy backend keeps the symbols.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin/Qt Designer plugin discovery.
- `BUILD_TESTING=ON` runs the upstream CTest autotests registered by the
  current headless feature set.
- Soname handling follows the device-verified kscreenlocker 6.7.2 pattern:
  the `CMAKE_SHARED_LIBRARY_SONAME_C(CXX)_FLAG` injection from 6.26.0.1 is
  dropped. With the OHOS CMake platform module absent, defining the flag
  makes CMake emit a versioned realname plus the `.so.6`/`.so` symlink
  chain, and the device kernel refuses symlinks on /storage - the first
  on-device `conan create` failed exactly at that link step. No variable is
  set instead (unversioned single `.so`, symlink-free) and patch 0002 stamps
  the basename `DT_SONAME` via a capability-gated `target_link_options`, so
  consumers still record the bare soname in `DT_NEEDED`; Linux keeps its
  platform soname handling because the gate opens only while the flag
  variable is undefined.
- `ECMQmlModule` include and `ecm_install_po_files_as_qm(poqm)` are disabled
  by patch for the minimal OHOS baseline (patch unchanged from 6.26.0.1;
  contexts verified against the 6.28.0 tree).
- Patch 0002 (`src/CMakeLists.txt`) is new in this refresh: it adds the
  capability-gated basename-soname link option described above.
- ECM 6.28 `KDEInstallDirs6` runs the qtbase `qtpaths` host tool at
  configure time; the recipe prepends `/system/lib64` (and the SDK llvm lib
  dir) to `LD_LIBRARY_PATH` so the compatible `libc++_shared.so` is found
  (bluez-qt 6.28.0 precedent).

## Verification

- Upstream source SHA256 verified:
  `5adbdf9c82b1ecbb92bda6498ea1b8f88c08f9ec57dbff70d582e2453bf16b12`
  (https://download.kde.org/stable/frameworks/6.28/kwindowsystem-6.28.0.tar.xz,
  tarball confirmed on the KDE mirror; the local copy was downloaded from
  mirrors.mit.edu/kde and its hash checked against the official .sha256).
- Patch 0001 applies cleanly to the unpacked 6.28.0 source
  (`patch -p1 --dry-run` OK on a pristine copy: hunk #1 at 26, hunk #2 at 86).
- Patch 0002 validated with conan's patch-ng applier (`strip=0`, chained with
  0001 on a fresh 6.28.0 extraction: both apply) and with `git apply
  --check` on the pristine tree. The GNU patch 2.7.6 build on the Windows
  workstation mis-matches byte-identical hunks on this host (reproduced on
  plain-text probe files - a host-tool defect unrelated to the patch), so
  the applicable verdict is the patch-ng one, the applier conan runs.
- On-device `conan create` completed green with both patches applied: the
  link step produced the unversioned `libKF6WindowSystem.so` with no symlink
  errors, `llvm-readelf -d` shows `SONAME: [libKF6WindowSystem.so]` on the
  packaged library and no symlinks exist in the package, and the
  test_package binary records the bare `libKF6WindowSystem.so` in its
  `DT_NEEDED`. CTest 1/1 passed, test_package 1/1 passed plus the runtime
  smoke output; package ID `57ffd8c720a5bfee7e8827990cd6550a49181c1b`. Gate
  summary: `reports/conan-verify-report.md` (verdict PASS).
- See manifest.yaml for the `conan create` result and test counts.
---

**编译结束**: 2026-10-16
**最终状态**: built
