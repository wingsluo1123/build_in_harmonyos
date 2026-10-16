# ktextwidgets 6.26.0 适配笔记

## 编译环境
- 构建系统: cmake（KDE ECM 工程）
- 编译日期: 2026-10-14
- 编译器: clang/clang++ 15.0.4（OHOS SDK）
- 状态: built（conan-verify G0-G4 全通过，待 CI 发布后置 published）
- 分支: feat/ktextwidgets-6.26.0

## 依赖
- qtbase/6.11.1（Qt6 Widgets）
- kcompletion/6.26.0.1（E537 修复版，DT_NEEDED 为 basename）
- kconfig/6.26.0、ki18n/6.26.0、kwidgetsaddons/6.26.0、sonnet/6.26.0
- ecm/6.26.0（tool_requires）

## 配方关键点
- `KF_IGNORE_PLATFORM_CHECK=TRUE`：绕过 KDE 平台白名单
- `KF_SKIP_PO_PROCESSING=ON`：跳过翻译目录生成
- `BUILD_TESTING=ON`：上游 5 个 CTest 全量执行
- `BUILD_DESIGNERPLUGIN=OFF`：Qt Designer 插件需要 Qt6UiPlugin（qtbase 未提供），设计期集成，库本体不受影响（kio 6.26.0 先例）
- `WITH_TEXT_TO_SPEECH=OFF`：qtexttospeech 未发布，仅影响 KTextEdit 朗读功能（kio 6.26.0 先例）
- `_library_runtime_env()` 对 OHOS prepend `/system/lib64`（libc++_shared.so 遮蔽修复）
- test_package 对齐 kcompletion 6.26.0.1 的 `../../bin` 相对 DT_NEEDED 兼容机制（sonnet/kconfig 制品携带相对路径 NEEDED）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package 加载 libKF6SonnetUi.so/libKF6ConfigGui.so 失败（../../bin/libKF6SonnetCore.so 相对 DT_NEEDED 无法解析） | sonnet/kconfig 制品发布时携带相对路径 DT_NEEDED（E537 相对路径变体） | test_package test() 在 build_folder/../../bin 建立依赖库符号链接 + LD_LIBRARY_PATH 追加依赖 lib（kcompletion 6.26.0.1 先例） |
| 2 | download.kde.org 本机 403 限流 | 官方源对大文件限流 | source() 加 USTC 官方镜像回退（同 sha256） |
| 3 | test_package KRichTextWidget 无默认构造 | KRichTextWidget 需 QWidget* parent | 显式传 nullptr |

## 测试
- 上游 CTest：**5/5 通过**（kfindtest, kreplacetest, krichtextedittest, ktextedit_unittest, kpluralhandlingspinboxtest）
- test_package：消费者链接 KF6::TextWidgets，KTextEdit + KRichTextWidget API → PASS

## 交付物
- conanfile.py、conandata.yml、manifest.yaml、notes.md、test_package/、patches/（0001-CMakeLists.txt.patch stamp IMPORTED_SONAME；0002-src-CMakeLists.txt.patch E537 裸 -l + PUBLIC -L + INTERFACE include）

## 对话记录
- 任务：ruqola 2.8.1 适配依赖链；kcompletion 6.26.0.1 E537 修复合入发布后恢复本包适配
- kcompletion PR #13965 已合入（merged），制品仓已发布（recipe 149a38ad）

**编译结束**: 2026-10-14
**最终状态**: built（待 CI 发布后置 published）
---

**编译结束**: 2026-10-14 19:07
**最终状态**: built
