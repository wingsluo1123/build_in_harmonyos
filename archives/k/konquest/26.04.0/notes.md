# konquest 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-18
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 源码获取: `download.kde.org/stable/release-service/26.04.0/src/konquest-26.04.0.tar.xz`
2. 依赖检查: qtbase/6.11.1, qtsvg/6.11.1, qtscxml/6.11.1, KF6 6.18.0, libkdegames/26.04.0 — 全部已发布
3. 补丁应用: patches/0001-cmake.patch — 移除 DocTools
4. conan create 通过 → test_package 通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libKDEGames6.so 运行时缺 OpenAL 符号 | libkdegames 依赖 openal-soft | test_package 增加 openal-soft/1.25.2 和 libsndfile/1.2.2 |
| 2 | konquest --version 输出 2.4.26040 而非 26.04.0 | 上游版本号格式为 BASE_VERSION.RELEASE_COMPACT | test.sh 更新匹配逻辑 |

## 源码修改

- patches/0001-cmake.patch:
  - 移除 KF6::DocTools（不在 KF6 闭包内）
  - 移除 add_subdirectory(doc) 和 kdoctools_install(po)
  - 注释掉 ecm_add_app_icon（避免 ECM 查找失败）

## 依赖版本

- qtbase/6.11.1
- qtsvg/6.11.1
- qtscxml/6.11.1
- karchive/6.18.0 (override=True)
- kcodecs/6.18.0
- kcolorscheme/6.18.0
- kconfig/6.18.0
- kconfigwidgets/6.18.0
- kcoreaddons/6.18.0
- kcrash/6.18.0
- kdbusaddons/6.18.0
- kguiaddons/6.18.0
- ki18n/6.18.0
- kwidgetsaddons/6.18.0
- kxmlgui/6.18.0
- libkdegames/26.04.0
- ecm/6.26.0 (tool_requires)

## 鸿蒙特有非断言测试（rule12）

test_package/test.sh 新增 OHOS musl loader NEEDED 闭包解析观测（非断言）：
逐项探测 23 个 NEEDED 条目在注入运行时库路径（LD_LIBRARY_PATH conan 依赖目录 + /system/lib64）
中的命中情况，输出观测报告（resolved=23 not-in-path=0），不改变退出码、不判定通过/失败；
测试通过与否仅由冒烟断言（--version + NEEDED 存在性）决定。

## 验证结果

```bash
conan create: PASS
test_package: konquest --version → "konquest 2.4.26040" ✅
upstream tests: N=0 (no tests/, autotests/ or add_test() in tarball)
```
---

**编译结束**: 2026-10-18 02:32
**最终状态**: built
