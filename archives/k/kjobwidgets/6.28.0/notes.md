# kjobwidgets 6.28.0 适配笔记

## 编译环境
- 构建系统: cmake（ECM 6.28.0，KF6 标准框架布局）
- 编译日期: 2026-10-18
- 编译器: clang/clang++（OHOS SDK clang 15，profile ohos-aarch64）
- conan: 2.29.1（OHOS 适配版），remote ohpcd
- 状态: built

## 背景（为何适配）
KF6 6.28 依赖链推进：kcoreaddons/kwidgetsaddons/knotifications 已发布 6.28.0，
消费方要求 KF6JobWidgets >= 6.28.0；ohpcd 当前最高 6.26.0。本包与 6.26.0 行为
一致（上游 6.26→6.28 差异仅版本号、ECM 版本与弃用告警门槛）。

## 真实依赖（kjobwidgets-6.28.0/CMakeLists.txt）
- ECM 6.28.0（tool_requires ecm/6.28.0）
- Qt6 Widgets >= 6.9.0（qtbase/6.11.1.1；Qt >= 6.10 时上游额外
  find_package(Qt6GuiPrivate)，该组件随 qtbase 包发布）
- KF6CoreAddons / KF6WidgetsAddons / KF6Notifications（均 6.28.0，已发布）
- 可选：Qt6 DBus（USE_DBUS）、X11（WITH_X11）、Python3+Shiboken6（BUILD_PYTHON_BINDINGS）

## 编译步骤

```bash
conan create archives/k/kjobwidgets/6.28.0 --build=missing -pr:h ohos-aarch64 -pr:b default
```

generate() 注入：ECM_MODULE_PATH 三段手工 set（CMakeDeps 不传播）；
qtbase cmake_find_mode=none → 手工生成 conan_cmakedeps_paths.cmake 把全部依赖的
lib/cmake、lib、include 前置；CMAKE_SHARED_LIBRARY_SONAME_*_FLAG 注入（E330）；
build/test 环境前置 /system/lib64（沙箱 libc++_shared.so 遮蔽，kconfig 先例）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | KDE 平台检查不含 OHOS | ECM 平台白名单 | KF_IGNORE_PLATFORM_CHECK=TRUE（kitemviews/knotifications 先例同款） |
| 2 | DBus job tracker 需要 Qt6DBus | qtbase/6.11.1 变体 FEATURE_dbus=OFF | 改用 qtbase/6.11.1.1（FEATURE_dbus=ON，dbus/1.14.10 已发布）+ override=True 统一依赖图；USE_DBUS=ON |
| 3 | WITH_X11 默认 ON（非 WIN/APPLE/ANDROID/HAIKU 平台） | OHOS 不在排除列表 | WITH_X11=OFF |
| 4 | Python 绑定需要 shiboken6 | 工具链无 Shiboken6 | BUILD_PYTHON_BINDINGS=OFF |
| 5 | OHOS 原生构建无 DT_SONAME | Generic 平台模块无 soname 规则 | 注入 CMAKE_SHARED_LIBRARY_SONAME_*_FLAG（E330/kcodecs 先例） |
| 6 | ecm_install_po_files_as_qm(poqm) 触发 find_package(Qt6LinguistTools) 失败 | qtbase 包未发布 LinguistTools 组件 | 补丁 0001 注释该调用（qm 翻译不构建；kconfig/6.26.0 先例同款） |
| 7 | 链接后 CMake 创建 libKF6JobWidgets.so.6 软链报 Permission denied（cmake_symlink_library） | HMDFS 用户卷拒 symlink（EPERM） | CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON（plain+cache 双写），产物为裸名 libKF6JobWidgets.so；kbookmarks/kservice 6.28.0 先例同款 |

## 源码修改

1 个补丁（patches/0001-disable-poqm-linguisttools.patch）：仅注释根
CMakeLists.txt 的 `ecm_install_po_files_as_qm(poqm)` 一行（Qt6LinguistTools
未发布 ohpcd；翻译 qm 产物非库功能），无其他改动。6.28.0 与 6.26.0 的
CMakeLists 差异仅在版本号与 ecm_set_disabled_deprecation_versions 的 KF
门槛（6.27.0），补丁上下文已按 6.28.0 重新生成。

## 依赖版本

qtbase/6.11.1.1（override=True，FEATURE_dbus=ON）、kcoreaddons/6.28.0、
kwidgetsaddons/6.28.0、knotifications/6.28.0、ecm/6.28.0（tool）。

## 验证结果

真机（OHOS 6.0 / clang 15 / conan 2.29.1）官方 conan-verify 通过：
G0 PASS、G1 PASS、G2 PASS（干净重建）、G3 PASS（纯库包，无系统同名库冲突）、
G4 PASS；L2/L4/L5 因无 cache 路径跳过（设备常态，等效覆盖在 test_package）。
报告：reports/conan-verify-report.md（Verdict: PASS）。

```bash
# 上游测试（R51 实测，2026-10-18，ctest --no-tests=error 强制注册数）：
# USE_DBUS=ON 解锁 HAVE_QTDBUS 守卫，ctest 注册 2 项并全部通过。
# 注册数若回归为 0，--no-tests=error 会让构建直接失败，而不是静默通过。
#   1/2 kuiserver2jobtrackertest  Passed 0.10 sec
#   2/2 kuiserver2jobtrackertest2 Passed 0.24 sec
#   100% tests passed, 0 tests failed out of 2
# test_package：ctest kjobwidgets_smoke 1/1 Passed；
# 消费者执行器逐例输出 TEST PASS 5 条 + TEST SUMMARY: 5 passed, 0 failed。
#   TEST PASS: KWidgetJobTracker construction        （inherits 检查，类身份可证伪）
#   TEST PASS: registerJob/unregisterJob round-trip  （widget() 映射插入/移除三态可观测）
#   TEST PASS: KDialogJobUiDelegate::setJob association
#   TEST PASS: KJob::setUiDelegate/uiDelegate round-trip
#   TEST PASS: KJob::setAutoDelete/isAutoDelete round-trip
```

验证报告 G4 的「无法找到程序包 ID」来自验证工具按 cache 路径检索（该路径在
当前设备不存在），实际 package_id / recipe revision 以下两行为准；L2/L4/L5
为无 cache 路径时的常规跳过（设备常态，功效由 test_package 覆盖）。

package_id: `3446ae520504bffb3ae7df79a2cf5d2a87c47f8b`；
recipe revision: `818b54ad9cc0a4a023befe4fc5ef0f42`；
lib/libKF6JobWidgets.so 的 DT_SONAME = `libKF6JobWidgets.so`（裸名，符合 E330/L5a）。

产物：lib/libKF6JobWidgets.so（裸名，无版本软链，DT_SONAME=libKF6JobWidgets.so）、include/KF6/KJobWidgets/ 头文件、
lib/cmake/KF6JobWidgets/（上游自带 KF6JobWidgetsConfig.cmake，cmake_find_mode=none）。

## 注意事项

1. 上游 KF6JobWidgetsConfig.cmake 自带依赖传播（find_dependency KF6CoreAddons 等），
   与 knotifications 同款用 cmake_find_mode=none 避免被 CMakeDeps 遮蔽。
2. 6.28.0 上游 autotests 与 6.26.0 逐字节一致；tests/ 下两个 GUI demo 仍由
   HAVE_QTDBUS 守卫，ctest 注册 2 项。
3. 未发布 ohpcd 制品仓（合入 main 后由 CI/维护者发布）。
