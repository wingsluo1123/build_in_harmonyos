# libkleo 26.04.3

此 HarmonyOS PC 配方位于 archives/l/libkleo/26.04.3。

上游测试口径：`autotests/CMakeLists.txt` 注册 16 个 CTest；`tests/CMakeLists.txt` 另有 8 个 `ecm_mark_as_test` 程序，未注册到 CTest。

设备隔离缓存 `CONAN_HOME=/data/storage/el2/base/cache/ch-lbk14632`。2026-10-04 同一次 `conan create` 完成编译、上游测试和 test_package，`CREATE_EXIT=0`。验证时导出为 `libkleo/26.04.3#54c7b75cb89277ba929dc9e708d3d674`，包 `bb1ea1271123679e5ae97eafd9152b3eddf3af6f#453efead063edfd4b1ae0afea6f9e03e`。补丁只在 `LIBKLEO_GNUPG_BIN` 非空时改引擎，不搜索 PATH。

- CTest 16/16 通过。日志原文：`100% tests passed out of 16`，`Total Test time (real) = 24.98 sec`。`keyresolvercoretest`、`expirycheckertest`、`classifytest` 均为 Passed。
- 8 个未注册程序都已启动。`test_cryptoconfig` 与 `test_keyformailbox` 退出码 0。`test_keyselectiondialog`、`test_keygen`、`test_keylister`、`test_auditlog`、`test_keyselectioncombo`、`test_keyresolver` 加载了 `libKPim6Libkleo.so.6`，停在上游 `QDialog::exec` 或 `QApplication::exec`。没有 `Error loading shared library`，也没有自动断言，不计为通过或失败。
- test_package 输出原文：`PASS: libkleo DN consumer API`。

gettext：同一隔离缓存上依赖图只有 ki18n/6.26.0 要求的 gettext/0.22.5#acfaf59091ac169d8112c896de1c84ee，没有第二个版本，也没有 Version ranges conflict。旧日志里的硬错误是 kconfig 缓存的 `conan_export.tgz already exists`。配方没有写 override。
