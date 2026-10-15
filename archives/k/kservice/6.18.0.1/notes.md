# kservice 6.18.0.1 notes

## 修订原因（相对 6.18.0）

- **补 XDG 菜单夹具（本次主因）**：上游 `ksycocatest` / `ksycoca_xdgdirstest` 需要 XDG 菜单文件
  `applications.menu`；QtTest 会把配置目录隔离到 `$HOME/.qttest/config`，而 6.18.0 配方
  只设了 `XDG_CONFIG_HOME=test-home/.config`，**没有投放该夹具** ⇒ CI 上 6 条 CTest 全部失败：
  `QCRITICAL: … "applications.menu" not found in QList("…/test-home/.qttest/config/menus")`、
  `FAIL!: KSycocaTest::ensureCacheValidShouldCreateDB() … returned FALSE`。
  本修订在 `_run_upstream_tests()` 里新增 `_prepare_xdg_menu_fixture()`：把
  `autotests/test-applications.menu`（源码树或构建树）拷成
  `$HOME/.qttest/config/menus/applications.menu`，找不到时写入最小兜底菜单。
- **共享库补 SONAME**：HarmonyOS 系统名在 CMake 里没有平台模块
  （构建日志 `System is unknown to cmake, create Platform/HarmonyOS`），
  `CMAKE_SHARED_LIBRARY_SONAME_*_FLAG` 为空 ⇒ `libKF6Service.so` 没有 SONAME，
  消费者会把**绝对路径**写进 `DT_NEEDED`。本修订在 `generate()` 里显式注入两条
  `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG = "-Wl,-soname,"`（与 `kio` 配方同法）。
- **打包期 ELF 自签名**：OHOS 只加载带有效 `.codesign` 的 ELF，`CMake.install()` 的复制
  会破坏签名；`package()` 现在对包内所有 ELF 重新
  `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` + `chmod 755`。
- **加载期修复兜底**：`_run_upstream_tests()` 在跑 ctest 前调用
  `_repair_absolute_needed_entries()`——对依赖链上残留的绝对 `DT_NEEDED`（指向 Conan 缓存）
  按 basename 软链补齐、已存在者重新自签名，避免被上游制品的缺陷拖红。
- **依赖 pin 对齐**：`qtbase/6.11.1` → `6.11.1.3`、`kconfig/6.18.0` → `6.18.0.1`、
  `kcoreaddons/6.18.0` → `6.18.0.1`、`ki18n/6.18.0` → `6.18.0.2`（均已发布）。
- **`conandata.yml` 补丁键同步**：`patches:` 的键由 `"6.18.0"` 改为 `"6.18.0.1"`
  （否则补丁静默失效，kcodecs 的教训）。

## Scope

This package is part of the KF 6.18 baseline. It adds a mainline-ready
`kservice/6.18.0` package directory without modifying other KF package recipes.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KF_SKIP_PO_PROCESSING=ON` avoids translation catalog generation.
- `BUILD_PYTHON_BINDINGS=OFF` avoids Shiboken/PySide requirements.
- `CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON` keeps optional docs out of the
  baseline package.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the OHOS
  Conan package build.
- Runtime/build dependencies use the current local KF baseline:
  `kconfig/6.18.0`, `kcoreaddons/6.18.0`, and `ki18n/6.18.0`; these dependency
  recipes are not included in this package PR.
- A minimal test-only MIME database is generated under the build folder and
  exposed through `XDG_DATA_DIRS`. It provides both
  `mime/packages/freedesktop.org.xml` for `QMimeDatabase` and per-type
  `mime/<type>.xml` entries for `KBuildMimeTypeFactory`, which is required by
  upstream service-trader and MIME association autotests on the current runner.
- `patches/0001-autotests-guard-ohos-fs-sensitive-checks.patch` guards two
  `ksycocatest` subtests behind the recipe-defined
  `KSERVICE_OHOS_SKIP_UNSUPPORTED_FS_TESTS=1` environment variable.

## Verification

Local and OHOS checks:

- Upstream source SHA256 verified locally:
  `d08aca74dcc54da29dd2b7bc404ed9e6ec688acc77839b4b8fbc372b5ea350b8`.
- Source patch applied:
  `patches/0001-autotests-guard-ohos-fs-sensitive-checks.patch`.
- Local syntax, patch, and whitespace checks passed:
  `python -m py_compile conanfile.py test_package/conanfile.py`,
  `git apply --check` against the 6.18.0 source tree, and `git diff --check`.

OHOS `conan create` verification passed on 2026-08-20.

- Runner log:
  `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/kservice-r4.log`.
- Full package reference:
  `kservice/6.18.0#2f92aa02c84df438bbfc83c9ff751d46:98bf041f61294dc9069e85c6ddafa905d2f55941#1706c9425b4b7b0da70d40f7807f5a09`.
- Runner gates:
  L0 pass, L1 pass, L2 skip (`kbuildsycoca6 --version/--help failed`), L4
  pass, L5 pass.
- L0 reported R36 for `kconfig/6.18.0` and `ki18n/6.18.0`: those dependencies
  were not yet published in the registry during the run and were consumed from
  the current local remote cache, as intended for this one-library PR.
- Upstream CTest passed 6/6:
  `ksycocatest`, `ksycoca_xdgdirstest`, `ksycocathreadtest`,
  `kservicetest`, `kapplicationtradertest`, and `kmimeassociationstest`.
- `ksycocatest` totals in `Testing/Temporary/LastTest.log`: 8 passed, 0
  failed, 2 skipped.
- Conan `test_package` passed 1/1 and printed
  `PASS: KService temporary service OK`.

## Upstream Tests Not Run

- `tests/kservicegroup_dumper`, `tests/findservice`, and
  `tests/kmimeassociations_dumper` were built, but upstream marks them with
  `ecm_mark_as_test()` and does not register them as CTest entries; they are
  manual helper executables, not part of the upstream CTest run.
- The AppStream metadata check was not set up because the current OHOS runner
  does not provide `appstreamcli`.
- Python bindings were not built or tested because `BUILD_PYTHON_BINDINGS=OFF`;
  those bindings require Shiboken/PySide and are outside this C++ baseline
  package.
- KF6DocTools documentation generation was not built because the recipe sets
  `CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON`; docs are optional and not part
  of the runtime package verification.

## Upstream Test Guards

- `KSycocaTest::testNonReadableSycoca` is skipped only when
  `KSERVICE_OHOS_SKIP_UNSUPPORTED_FS_TESTS=1` and the current runner can still
  open a sycoca file after it has been set to `QFile::WriteOwner`. The test is
  intended to simulate an unreadable/root-owned cache file; that precondition is
  false on this runner.
- `KSycocaTest::extraFileInFutureShouldRebuildSycocaOnce` is skipped only when
  `KSERVICE_OHOS_SKIP_UNSUPPORTED_FS_TESTS=1` and the rebuilt sycoca timestamp
  does not become strictly newer than the old timestamp. The current runner's
  filesystem timestamp behavior does not satisfy that strict mtime
  precondition for this subtest.
