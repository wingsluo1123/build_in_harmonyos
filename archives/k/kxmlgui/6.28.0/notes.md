# kxmlgui 6.28.0 适配笔记

## 编译环境
- 构建系统: cmake (ECM 6.28.0)
- 编译日期: 2026-10-18
- 编译器: clang/clang++ (OHOS SDK, aarch64-linux-ohos)
- 状态: built

## 软件简介

kxmlgui 是 KDE Frameworks 6 的 XML GUI 框架库（libKF6XmlGui.so）：为
KMainWindow/KXmlGuiWindow 提供基于 XML 的菜单/工具栏描述、动作集合
（KActionCollection）、快捷键编辑器（KShortcutsEditor）等。

本件是 KF6 6.28 线升级，基于已验证的 6.26.0 配方骨架 + 6.28.0 源码。

## 与 6.26.0 配方的差异

| # | 变更 | 原因 |
|---|------|------|
| 1 | 配方版本 6.26.0 → 6.28.0；源码 URL/sha256 更新为 6.28.0 | 上游 6.28 列车 |
| 2 | `tool_requires` ecm 6.26.0 → 6.28.0 | 6.28 源码按 ECM 6.28 的 KDEInstallDirs6 构建；ohpcd 已发布 ecm/6.28.0 |
| 3 | 补丁 0001 增加 `KF_DEP_VERSION` 6.28.0 → 6.26.0 降档 hunk | KF6 6.28 列车未发布到 ohpcd（kconfig/kcoreaddons/kguiaddons/ki18n/kiconthemes/kitemviews/kwidgetsaddons 均仍为 6.26 线）；6.26.0 是满足全部 find_package 的公共地板 |
| 4 | 补丁 0001/0002/0003/0004 重生成到 6.28 源码 | 6.28 源码行号偏移（0003 结构未变，行号 +5） |
| 5 | 新增 CMAKE_PLATFORM_NO_VERSIONED_SONAME + 显式 -soname 变量（plain 与 cache 双份） | HMDFS 拒 symlink()（EPERM），带版本号的 .so 链无法在设备上创建；同时保证 lld 产出 DT_SONAME（kbookmarks 6.28.0 先例） |
| 6 | configure/build 走 `_cmake_build_env()`：LD_LIBRARY_PATH 前置 SDK llvm lib 与 /system/lib64 | ECM 6.28 KDEInstallDirs6 在 configure 期运行 qtbase qtpaths 宿主工具，沙箱 libc++_shared.so 会遮蔽兼容版本（kbookmarks 6.28.0 先例） |
| 7 | test_package 改为 6 用例执行器 | rule12 要求消费者端到端用例：逐例 TEST PASS/FAIL + TEST SUMMARY + 任一失败 exit 1 |

依赖矩阵与 6.26.0 一致（kconfigwidgets/6.18.0 cap + override 到 6.26 线），
原因见下节。

### KF_DEP_VERSION 降档与 6.28 API 兼容性

6.28 源码 `set(KF_DEP_VERSION "6.28.0")` 会让
`find_package(KF6CoreAddons 6.28.0 REQUIRED)` 等全部失败（ohpcd 无 6.28 制品）。
补丁 0001 将其降为 6.26.0。

6.28 新增代码路径对 6.26 依赖的 API 需求已逐一核对：
- `KKeySequenceRecorder::Pattern`（kguiaddons，6.26.0 已有该 enum）
- `KToolBarPopupAction`（kxmlgui 自身类，随本源码树构建）
- KStandardActions::keyBindings（kconfigwidgets，6.18.0 已有）

## 依赖核验（W0，R35 conan download 口径）

qtbase/6.11.1 ✅ kconfig/6.26.0 ✅ kcoreaddons/6.26.0 ✅
kguiaddons/6.26.0 ✅ ki18n/6.26.0 ✅ kiconthemes/6.26.0 ✅
kitemviews/6.26.0 ✅ kwidgetsaddons/6.26.0 ✅ openssl/3.5.6.1 ✅
zstd/1.5.7 ✅ ecm/6.28.0 ✅ kconfigwidgets/6.18.0 ✅（cap）
kcolorscheme/6.26.0 ✅ kcodecs/6.26.0 ✅（override 目标）

## 编译步骤

conan create：
```
conan create archives/k/kxmlgui/6.28.0 \
  -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b ~/.conan2/profiles/ohos-aarch64 \
  --build=missing
```
关键 CMake 配置：
- `-DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=ON`
- `-DKF_IGNORE_PLATFORM_CHECK=TRUE`（OHOS 不在 KDE 平台列表）
- `-DFORCE_DISABLE_KGLOBALACCEL=ON`（KF6GlobalAccel 未发布）
- `-DUSE_DBUS=OFF`（qtbase 基线无 Qt6DBus）
- `-DBUILD_DESIGNERPLUGIN=OFF`（Qt6UiPlugin 未发布）
- `-DBUILD_PYTHON_BINDINGS=OFF`（无 Shiboken6/PySide6）
- `-DKF_SKIP_PO_PROCESSING=ON`（无 Qt6LinguistTools）
- `-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` + SONAME flags（HMDFS）
- ECM_MODULE_PATH 手工注入（CMakeDeps 生成的 ECMConfig 不传播该变量）
- conan_cmakedeps_paths.cmake 手工生成（qtbase cmake_find_mode=none）

## 上游测试（N=82 审核员实测口径）

上游测试体系三层构成（BUILD_TESTING=ON 下 autotests + tests 全集）：

1. **autotests/**（ecm_add_tests 注册 6 个 CTest 目标，74 个 QTest 函数/槽定义）：
   全树 `void 类::函数(` 类外定义 81 处，剔除 7 个
   initTestCase/cleanupTestCase 生命周期定义（initTestCase 4、cleanupTestCase 3；
   无 benchmark 函数）= 74。其中 68 个为测试/准备槽（`rule4-count.py` 口径，
   剔除生命周期与 `*_data`）：kactioncategorytest(3) kactioncollectiontest(16)
   kmainwindow_unittest(10) ktoolbar_unittest(12) ktooltiphelper_unittest(4)
   kxmlgui_unittest(23)；另 6 个为 `*_data` 数据提供函数（ktoolbar 4、kxmlgui 2）。
2. **tests/**（8 个手动 GUI 验证程序，`ecm_mark_as_test` 只标记构建归属、
   不执行 add_test，上游设计为手动运行）：
   kbugreporttest kmainwindowrestoretest kmainwindowtest krulertest
   ktoolbartest kwindowtest kxmlguitest kxmlguiwindowtest。
3. **tests/krichtexteditor**（1 个，KTextWidgets 条件构建；未发布→不构建，豁免）。

声明口径 = 74（QTest 函数/槽定义）+ 8（tests/ GUI）= **N=82**，与 6.26.0
审核员实测口径一致。6.26→6.28 的 autotests/、tests/ 源码逐字节一致
（diff -rq 全同；仅 0004 补丁触及的 kxmlgui_unittest.cpp 因本包补丁而异）。

真机复验结果（QT_QPA_PLATFORM=offscreen，干净 test-home）：`conan create` 内
`ctest --test-dir <build> --output-on-failure --no-tests=error` 返回 0，
6/6 CTest 程序全数 Passed（任一失败即中止构建；G2 门禁已过）；test_package
`TEST SUMMARY: 6 passed, 0 failed`。`tests/` 8 个手动 GUI 程序随
`BUILD_TESTING=ON` 全数构建产出（上游 `ecm_mark_as_test` 不注册 CTest，
设计为手动运行）。

0004 补丁整改后（运行时门槛 + `QEXPECT_FAIL(..., Continue)`）再次真机复验：
G0–G4 全 PASS、`VERIFY_EXIT=0`；ctest 6/6 程序全数 Passed；test_package
单次执行、干净 HOME/XDG 状态下 `TEST SUMMARY: 6 passed, 0 failed`。该门槛不改
通过/失败判据：`$LANGUAGE` 未被更新时原比较照常硬失败，预期失败行若通过
（XPASS）亦判失败。

R2 整改（补丁应用位置）：`apply_conandata_patches(self)` 由 `build()` 移入
`source()` 中 `get(...)` 之后。Conan 2 的源目录按 recipe revision 共享，
`build()` 按包配置执行；补丁留在 `build()` 会让第二个配置在已打补丁源码上
重复应用（`patch_ng` 按 "previously applied" 抛错），且 `conan source` 产物
与实际编译源码不一致。`conandata.yml` 中 0004 的 patch_description 同步为
运行时门槛 + `QEXPECT_FAIL(Continue)` 语义。

- 注意：复验时 test-home 必须干净——kxmlgui_unittest 的
  testHiddenToolBar/testAutoSaveSettings 依赖 KConfig 状态，污染的
  test-home 会产生假失败（6.26 实测：干净 43/43 过 vs 污染 41+2 败）。
  配方每次全新 test-home 的设计正是为此。
- krichtexteditor 豁免：KTextWidgets 未发布到 ohpcd，上游
  `find_package(KF6TextWidgets QUIET)` 查找失败不构建该子目录。
