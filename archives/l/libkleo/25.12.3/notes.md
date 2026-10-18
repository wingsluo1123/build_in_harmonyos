# libkleo 25.12.3 OHOS Port Notes

## Scope

This recipe stages `libkleo/25.12.3` for the Akonadi calendar dependency
chain. It builds the KDE PIM Kleopatra support library as a shared CMake
package on OHOS.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` and `KF_SKIP_PO_PROCESSING=ON` keep the build
  on the current OHOS Qt/KF package baseline.
- Upstream uses several C++20 `std::ranges` algorithms that are not available
  in the OHOS libc++15 headers. Patch `0001-avoid-ranges-algorithms-on-libcxx15.patch`
  rewrites these call sites to equivalent standard algorithms.
- The recipe keeps `BUILD_TESTING=ON` but excludes tests that require a live
  GnuPG agent, interactive key selection, or GUI dialogs.
- The consumer `test_package` verifies that the exported Libkleo CMake target
  can be found and linked with Qt6 Core/Widgets.

## Current Blockers

- `libkleo` requires GpgME C++/Qt CMake targets. The published
  `gpgme/1.24.0` package exposes the base C binding only, so this recipe now
  requires `gpgme/1.24.0.1`, which republishes upstream GPGME 1.24.0 with
  `Gpgmepp` and `QGpgmeQt6` package config files.
- Real-device local verification is temporarily unavailable, so final OHOS
  validation is delegated to PR CI.

## Validation

- 2026-08-31: local `python -m py_compile` passed for `conanfile.py` and
  `test_package/conanfile.py`.
- 2026-08-31: `test_package/MANIFEST.yml` exists and no `MANIFEST.MF` file is
  present.
- 2026-09-01: PR CI #35485 confirmed the previous `gpgme/1.24.0` dependency
  fails at `find_package(Gpgmepp)`. The recipe was updated to
  `gpgme/1.24.0.1`; it must be rerun after that package PR is published.

## Runtime DT_NEEDED repair (2026-10-12)

- 部分 KF6 依赖（如 `kguiaddons/6.18.0`）**没有 SONAME**，链接它的消费者因此把
  **绝对路径**写进 `DT_NEEDED`；该路径在测试机上不存在，或指向被复制后 `.codesign`
  失效的库。表现是本包 12 个上游用例全挂：
  `Error loading shared library .../libKF6GuiAddons.so (needed by .../libKF6ColorScheme.so)`
  紧跟 `KColorUtils*/KColorSchemeWatcher* symbol not found`。
- `_repair_absolute_needed_entries()` 在运行上游 CTest 前扫描测试树与依赖包的 ELF：
  对缺失的绝对路径按 basename 在依赖包中找到同名库并建软链；对已存在者重新自签名。
  真机上同一手法（对 warm home 的库重签 + 建 6 条兼容 symlink）曾把本包上游 CTest
  从 0/12 恢复到 12/12。
- `_sign_ohos_elf_tree()` 改为复用新的单文件 `_sign_ohos_elf()`，行为不变（仍要求
  `binary-sign-tool` 存在，否则报错）。
