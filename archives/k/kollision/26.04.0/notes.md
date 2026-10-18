# kollision 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake (ECM/KDE CMake toolchain)
- 编译日期: 2026-10-18
- 编译器: clang 15 / clang++
- 状态: published
- 目标平台: HarmonyOS PC (arm64)

## 编译步骤

1. `ohc-run.py init-build kollision 26.04.0 --url=https://download.kde.org/stable/release-service/26.04.0/src/kollision-26.04.0.tar.xz` → 源码下载到 `/data/storage/el2/base/cache/builds/kollision-26.04.0.work`
2. `ohc-run.py conan-init kollision 26.04.0` → 生成 conanfile.py (klickety 模板)
3. 源码修改：CMakeLists.txt 移除 DocTools + doc/ (0001-cmake.patch)
4. 手动创建 test_package/ (klickety 模板)
5. `ohc-run.py conan-verify kollision 26.04.0` → G0-G4 + L2/L4/L5 全绿
6. `conan create` (CI mode) → exit 0, test_package 全通过 (2/2 断言)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 失败：`Unknown CMake command "kdoctools_create_handbook"` | 上游默认 `find_package(DocTools REQUIRED)` + `kdoctools_install(po)` 但 kdoctools 不在 KF6 6.18/6.26 闭包 | 补丁 0001 移除 DocTools + doc/ 子目录 + kdoctools_install (klickety 先例) |
| 2 | 补丁无效 (invalid hunk at line 40) | 初始补丁行号与 kollision 实际源码不匹配 (CoreAddons→Crash) | 用 `diff -u` 基于源码副本重新生成 |
| 3 | 补丁拒绝：absolute paths not allowed | diff 使用绝对路径而非 a/ b/ 相对路径 | 将补丁首行改为 `--- a/CMakeLists.txt` / `+++ b/CMakeLists.txt` |

## 源码修改

- `patches/0001-cmake.patch`: 移除 KF6::DocTools 依赖、doc/ 子目录、kdoctools_install(po) 调用 (kdoctools 不在 KF6 6.18 闭包，手册非运行时必需)

## 依赖版本

| 包 | 版本 |
|-----|-----|
| qtbase | 6.11.1 |
| qtsvg | 6.11.1 |
| karchive | 6.18.0 (override) |
| kcolorscheme | 6.18.0 |
| kcompletion | 6.18.0 |
| kconfig | 6.18.0 |
| kconfigwidgets | 6.18.0 |
| kcoreaddons | 6.18.0 |
| kcrash | 6.18.0 |
| kdbusaddons | 6.18.0 |
| kguiaddons | 6.18.0 |
| ki18n | 6.18.0 |
| kiconthemes | 6.18.0 |
| knewstuff | 6.18.0 |
| kwidgetsaddons | 6.18.0 |
| kxmlgui | 6.18.0 |
| libkdegames | 26.04.0.1 |
| ecm | 6.26.0 (tool_requires) |

## 验证结果

```
conan-verify: G0 PASS, G1 PASS, G2 PASS, G3 PASS, G4 PASS, L2/L4/L5 PASS
conan create: exit_code=0
test_package: kollision --version → "kollision 0.3.26040" ✅
upstream tests: N=0 (无上游测试)
```

## 适配模式 (klickety 26.04.0 先例)

- KF_IGNORE_PLATFORM_CHECK=TRUE
- KF_SKIP_PO_PROCESSING=ON
- karchive/6.18.0 override=True pin
- -Wl,-z,max-page-size=0x1000 链接器标志
- ECM_MODULE_PATH + conan_cmakedeps_paths.cmake 手动配置 (cmake_find_mode=none 包)
- test_package 必须实质运行被测二进制 (L0c/R34)

## 积分赛适配

- manifest.knowledge_gained 保留 (积分赛必填)
- 不提交知识草稿 (积分赛不交 drafts)
---

**编译结束**: 2026-10-18 03:15
**最终状态**: published
