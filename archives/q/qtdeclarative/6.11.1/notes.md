# qtdeclarative 6.11.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-08（初始）/ 2026-08-13（复审验证）
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `ohc-run.py init-build qtdeclarative 6.11.1 --url=<qtdeclarative-everywhere-src-6.11.1.tar.xz 镜像>`
2. CMake 配置（conan create 内部）：`OhosLinuxPlatformBlock` 将 `CMAKE_SYSTEM_NAME` 映射为 Linux（OHOS clang 驱动目标为 aarch64-unknown-linux-ohos，使 CMake 采用标准共享库 SONAME/版本规则）；`QT_QMAKE_TARGET_MKSPEC=harmonyos-clang`；`CMAKE_PREFIX_PATH=<qtbase 包>`；`QT_ADDITIONAL_PACKAGES_PREFIX_PATH=<qtshadertools 包>`（提供 qt_internal_add_shaders 宏）
3. `cmake --build` 生成 libQt6Qml.so / libQt6QmlModels.so / libQt6QmlWorkerScript.so 等
4. 构建期 qsb（Qt Shader Baker）预烘焙 scene-graph shader：`conanbuild_qt_libs` 环境脚本把 qtbase/qtshadertools 的 lib 注入 LD_LIBRARY_PATH
5. `conan-verify` 8 道门禁（G0-G4 + L2/L4/L5）全部通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 无 Platform/HarmonyOS.cmake，共享库 SONAME 规则失败 | OHOS host 上 CMake 自动检测 CMAKE_SYSTEM_NAME=HarmonyOS 后无对应平台规则 | 自定义 CMakeToolchain Block 将 CMAKE_SYSTEM_NAME 映射为 Linux（clang 驱动仍目标 aarch64-unknown-linux-ohos） |
| 2 | qsb 宿主工具构建期加载依赖失败 | qsb RUNPATH 仅覆盖自身包 lib，找不到 libQt6Core/libQt6Gui | generate() 生成 conanbuild_qt_libs 环境脚本注入 LD_LIBRARY_PATH |
| 3 | HMDFS 破坏 install 相对符号链接（E215） | install 时相对 symlink 在 HMDFS 上失效 | package() 中 _ensure_soname_symlinks 重建 libQt6Qml.so/.so.6 等链接 |
| 4 | OHOS 可执行 ELF 需签名 | 未签名的 ET_EXEC/ET_DYN 无法在 OHOS 运行 | _sign_installed_elfs 用 binary-sign-tool 重签所有 ELF（含 .codesign 校验） |

## 源码修改

无补丁（0 个）：qtdeclarative 适配全部在配方层完成（平台映射 Block、LD_LIBRARY_PATH 注入、SONAME 符号链接修复、ELF 重签），无需修改上游源码。

## 依赖版本

- qtbase/6.11.1（Qt6Config.cmake + harmonyos-clang mkspec + libQt6Core/Gui）
- qtshadertools/6.11.1（qt_internal_add_shaders CMake 宏 + qsb 宿主工具）

## 验证结果

```bash
# conan-verify（G0-G4 + L2/L4/L5）
G0-G4 全 PASS，可标记 status: published
# test_package 消费者测试（QQmlEngine/QQmlComponent/QJSValue 实质 QML smoke test）
qtdeclarative consumer test: ALL PASSED
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml | Conan 配方（CMake + qtbase/qtshadertools 依赖，5 镜像 URL） |
| test_package/ | 消费者测试（QML engine/component/JS 求值实质断言） |
| reports/ | conan-verify-report.md、test-report.md、audit-result.json |

## 注意事项

- 基于协作者分支 feat/qtdeclarative-6.11.1-A8CF（commit 07a5496a0）继续：配方层适配完整（平台映射/SONAME/签名），补齐验证流程（conan-verify/finish/W4/PR）。
- qtdeclarative 依赖 qtshadertools（qt_internal_add_shaders 宏），发布顺序 qtbase → qtshadertools → qtdeclarative。
- 无显示环境：QML 测试需 QT_QPA_PLATFORM=offscreen（如适用）。
---

**编译结束**: 2026-08-13 14:20
**最终状态**: published
