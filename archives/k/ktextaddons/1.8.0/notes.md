# ktextaddons 1.8.0 notes

## Scope

This package provides the KTextAddons targets currently needed by the Akonadi
downstream chain:

- `KF6::TextUtils`
- `KF6::TextAddonsWidgets`
- `KF6::TextEmoticonsCore`
- `KF6::TextEmoticonsWidgets`
- `KF6::TextCustomEditor`

## Adaptations

- The root build is patched to build only the component subset listed above.
- `BUILD_QUICK=OFF` keeps Qt Quick support disabled.
- `BUILD_KIO_SUPPORT=OFF` keeps optional TextCustomEditor web shortcut menu
  support disabled. The affected runtime property remains `false`; upstream
  tests are patched to assert the configured feature state instead of assuming
  KIO support is always compiled in.
- `BUILD_DESIGNERPLUGIN=OFF` keeps the Qt Designer plugin disabled.
- `BUILD_QCH=OFF` skips Qt Assistant documentation.
- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables the KDE Frameworks build on OHOS.
- `KF_SKIP_PO_PROCESSING=ON` skips translation catalog generation.
- `BUILD_TESTING=ON` keeps the upstream tests for the built components enabled.
- The test runtime pins `QT_QPA_PLATFORM_PLUGIN_PATH` to the Qt platform plugin
  directory so Widgets tests can load the offscreen platform plugin.

## Verification

OHOS `conan create` passed:

- Upstream CTest: 27/27 registered tests passed.
- `test_package`: 1/1 passed, including installed CMake discovery, link, CTest,
  and direct runtime smoke for `KF6::TextUtils`, `KF6::TextAddonsWidgets`,
  `KF6::TextEmoticonsCore`, `KF6::TextEmoticonsWidgets`, and
  `KF6::TextCustomEditor`.
- Full reference:
  `ktextaddons/1.8.0#0483052346bc04d5e1d8c63414a723d8:80c4ac0b7a3bd9351208a8256643d4769dbff1de#f0ba612a65f116fa00aa395b18f82b43`.

Not executed:

- Tests for the disabled KTextAddons component families are not registered
  because those components are not built in this package. They pull optional
  KIO/web-shortcut, Keychain, Qt Multimedia, Qt TextToSpeech, speech-to-text,
  grammar, translator, autocorrection, and generated-text plugin chains that
  are outside the current Akonadi downstream requirement and are handled as
  separate dependency work rather than hidden inside this package.
- Qt Quick support is disabled with `BUILD_QUICK=OFF`; it is not required by
  the selected KTextAddons targets.
- The Qt Designer plugin is disabled with `BUILD_DESIGNERPLUGIN=OFF`; it is an
  IDE integration artifact and not needed by library consumers.
- `ECMCheckOutboundLicense`/ReuseTool checks are optional and are not registered
  because `reuse` is unavailable in the OHOS packaging profile.
- `appstreamcli` validation is optional and is not registered because the tool
  is unavailable in the OHOS packaging profile.
- Qt Assistant documentation targets are disabled with `BUILD_QCH=OFF`.

## Runtime DT_NEEDED repair (2026-10-12)

- 部分 KF6 依赖（如 `kguiaddons/6.18.0`）**没有 SONAME**，链接它的消费者因此把
  **绝对路径**写进 `DT_NEEDED`；该路径指向构建机的 Conan 缓存，在测试机上不存在，
  或指向被复制后 `.codesign` 失效、OHOS 加载器拒绝加载的库。表现是所有链接该库的
  用例一起失败（`Error loading shared library .../libKF6GuiAddons.so (needed by .../libKF6ColorScheme.so)`
  紧跟 `KColorUtils*/KColorSchemeWatcher* symbol not found`）。
- `_repair_absolute_needed_entries()` 在运行上游 CTest 前扫描测试树与依赖包的 ELF：
  对缺失的绝对路径按 basename 在依赖包中找到同名库并建软链；对已存在者重新自签名
  （`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`）。
  真机上同一手法（手工 symlink + 重签）曾把本包上游 CTest 从 18/32 恢复到 32/32。
- `package()` 追加 `_sign_ohos_package_elfs()`：对包内所有 ELF 重新自签名，避免
  shared 消费者运行期加载失败（与 `knotifications/6.18.0.1`、`libkleo` 同法）。
