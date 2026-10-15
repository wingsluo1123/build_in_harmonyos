# kactivitymanagerd 6.7.2 适配笔记

## 编译环境
- 构建系统: CMake (ECM/Ninja via Conan CMakeToolchain)
- 编译日期: 2026-10-13
- 编译器: HarmonyOS OHOS SDK clang/clang++ (aarch64-linux-ohos)
- 状态: published

## 编译步骤
Conan 全流程适配（conan create），`build()` 中 CMake configure + build：
- 工具链依赖 `ecm/6.26.0` + `qt6linguisttools/6.11.1`（ki18n_install po 处理需要 lrelease）
- `cmake_layout` + `cmake.build()`；安装按 KDEInstallDirs Linux 布局：
  守护进程 `bin/kactivitymanagerd`，插件 `lib/plugins/kactivitymanagerd1/*.so`
- `package()` 末尾执行 patchelf NEEDED 重定位清扫（见问题 #6）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI 补丁拆分器不支持新增/删除文件 | conandata patches 只能修改既有文件 | 文件重命名与 XML 注入改在 `source()` 内用 Python 完成 |
| 2 | `libc++` `<features.h>` 与项目 `src/service/Features.h` 冲突（大小写不敏感文件系统） | 同名头文件解析错序 | `source()` 中重命名 Features.h/cpp → FeaturesIface.h/cpp，并同步修正 `#include "FeaturesIface.h"` 与 AUTOMOC 的 `moc_FeaturesIface.cpp` 引用 |
| 3 | `version.h` 与 `src/service/Version.h` 冲突 | 同名头文件 | 补丁将生成的 version.h 改名为 kactivitymanagerd_version.h |
| 4 | KDirNotify DBus 接口缺失（`kdirnotifygenerated.h`、emit 静态助手） | 发布 kio 包无 DBus 特性、无 kdirnotify.h | `source()` 内嵌 org.kde.KDirNotify.xml，`0004` 补丁用 `qt_add_dbus_interface` 本地生成；emit 助手缺失处用手写 QDBusMessage 信号函数（0005 补丁） |
| 5 | KF6DBusAddons ≥6.26.0 但发布 kdbusaddons 只有 6.18.0/6.29.0 | 版本需求 | 采用 kdbusaddons/6.29.0，qtbase 用 `qtbase/6.11.1.1` override 对齐；DBus 能力由 `qtbase-sql-dbus/6.11.1` 提供（kglobalaccel 先例），generate() 中在依赖循环后再次 PREPEND 其 cmake 路径保证 find_package(Qt6) 命中 Qt6::DBus |
| 6 | L5b: 产物 DT_NEEDED 含 Conan 缓存绝对路径 | 依赖 kdbusaddons/6.29.0、ki18n/6.26.0、kcrash/6.26.0 的 .so 无 DT_SONAME，链接器记录完整路径 | `package()` 中用 patchelf `--replace-needed` 把绝对路径 NEEDED 改写为 basename（alkimia/8.2.1 先例），运行时经 LD_LIBRARY_PATH 解析 |
| 7 | SONAME 缺失 | HarmonyOS 无 Platform 模块导致 `CMAKE_SHARED_LIBRARY_SONAME_*_FLAG` 未定义 | 设置 `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG = -Wl,-soname,`（kglobalaccel 先例） |
| 8 | source() 禁止访问 self.settings | Conan 2 约束 | 移除 `if self.settings.os == "OHOS"` 条件，重命名/XML 注入无条件执行 |
| 9 | test_package 冒烟无法解析插件依赖 | `self.run()` 默认用 conanbuild 环境，Environment() 变量不生效 | 把 `LD_LIBRARY_PATH`/`QT_QPA_PLATFORM` 内联进命令行 |

## 源码修改（conandata 补丁 + source() 处理）
- `0001-CMakeLists.txt.patch`: 生成的 version.h → kactivitymanagerd_version.h
- `0002-src-service-Application.cpp.patch`: include 修正 + FeaturesIface.h
- `0003-src-service-CMakeLists.txt.patch`: find_package(KF6Service)、FeaturesIface dbus adaptor
- `0004-src-service-plugins-sqlite-CMakeLists.txt.patch`: qt_add_dbus_interface 生成 KDirNotify
- `0005-src-service-plugins-sqlite-ResourceLinking.cpp.patch`: 使用 kdirnotifygenerated.h + 手写 QDBusMessage 信号助手
- `source()`: Features.h/cpp → FeaturesIface.h/cpp（含 moc 引用同步）、内嵌 KDirNotify XML

## 依赖版本
qtbase-sql-dbus/6.11.1、qtbase/6.11.1.1 (override)、kdbusaddons/6.29.0、kcoreaddons/6.26.0.1、kcrash/6.26.0、ki18n/6.26.0、kconfig/6.26.0、kglobalaccel/6.26.0、kxmlgui/6.26.0、kio/6.26.0、boost/1.85.0、zlib/1.3.2 (override)；tool_requires: ecm/6.26.0、qt6linguisttools/6.11.1

## 验证结果
```bash
# W3 本地 CI: 全部通过（exit 0）
# conan-verify G2: ✅ 配方验证通过
# 冒烟: timeout 60 运行守护进程，exit 0（无 session bus 优雅退出）或 124（存活被杀）均视为通过
```

## 注意事项
- 本包为 D-Bus 守护进程应用，无上游测试套件；test_package 采用守护进程冒烟（smoke_test.sh）
- `cpp_info.bindirs = ["bin"]`（实际安装位置，非 libexec）
- 下游若链接本包插件库，运行时需保证 LD_LIBRARY_PATH 包含本包 lib/（KF6 依赖库均无 SONAME）

---
**编译结束**: 2026-10-13 23:04
**最终状态**: published
---

**编译结束**: 2026-10-13 23:19
**最终状态**: built

## 运行时依赖桥接（2026-10-14，E537 家族）
- 已发布的 `kcrash/6.26.0` 二进制 `libKF6Crash.so` 将 `libKF6CoreAddons.so` 烙印为发布机
  conan 缓存的绝对路径（DT_NEEDED 含 `/`），loader 不回退 LD_LIBRARY_PATH；conan2 的
  `p/<random>/` 目录名逐机随机，导致在任何缓存布局不同的机器上运行时加载失败
  （CI 构建 #91762 的 smoke test "Error loading shared library ... libKF6CoreAddons.so"）。
- 修复：`package()` 新增 `_bridge_dep_absolute_needed()` — 扫描依赖包全部 .so 的
  DT_NEEDED，对"绝对路径且不存在且位于 conan2 缓存内"的条目，在烙印路径处创建
  symlink 指向依赖图中同名真实库（fontconfig/DRAFT-E5xx 先例；不改 ELF 内容，签名有效；
  幂等：路径已存在则跳过）。
- 长期修复应在 kcrash（及 ki18n/kdbusaddons 等同类包）侧重打包；本桥接仅保证本包
  在任意机器上可运行与冒烟通过。
