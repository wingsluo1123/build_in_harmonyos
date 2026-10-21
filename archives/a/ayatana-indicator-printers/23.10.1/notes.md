# ayatana-indicator-printers 23.10.1 适配笔记

## 软件简介

Ayatana 系统指示器家族的打印机指示器：守护进程 `ayatana-indicator-printers-service`
在系统总线上订阅 CUPS 通知接口 `org.cups.cupsd.Notifier`，在会话总线上占用
`org.ayatana.indicator.printers` 并导出指示器菜单（`org.gtk.Actions` +
`org.gtk.Menus`）。产物为**守护进程二进制**（`libexec/ayatana-indicator-printers/`）
加数据文件（指示器描述文件 `org.ayatana.indicator.printers`、autostart
`.desktop`），**无公共库**。

## 编译环境

- 构建系统: cmake（上游 `CMakeLists.txt`，init-build 误判为 autotools，已人工复核修正）
- 编译日期: 2026-10-16
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 目标平台: HarmonyOS PC aarch64（os=OHOS，arch=armv8）
- 状态: built（本地 conan create + 门禁验证通过）

## 依赖（W0 预检，全部为已发布制品）

| 上游依赖 | Conan 包 | 说明 |
|---|---|---|
| `glib-2.0>=2.36` / `gio-2.0>=2.36` | `glib/2.84.0.1` | `pkg_check_modules(SERVICE REQUIRED ...)` |
| `gio-unix-2.0>=2.36` | 同上（glib 包内 `.pc`，见下） | glib 配方未导出该组件 |
| `libayatana-common` | `ayatana-common/0.9.11` | pkg_config_name = `libayatana-common` |
| `find_program(cups-config)` + `cups/cups.h` | `cups/2.4.19` | 源码 `src/indicator-printers-service.c` 无条件 `#include <cups/cups.h>` |

> `cups/2.4.19` 依赖 `zlib/1.3.1.1`，与 `glib/2.88.0.1` 的 `zlib/1.3.1.1.1.1`
> 冲突（`Version conflict: zlib/1.3.1.1 vs zlib/1.3.1.1.1.1`）；改用
> `glib/2.84.0.1` + `ayatana-common/0.9.11`（同为 `zlib/1.3.1.1` track）即可收敛。
>
> `W0` 预检：`bash ci/scripts/preflight_check.sh ayatana-indicator-printers/23.10.1
> --deps "glib/2.84.0.1 ayatana-common/0.9.11 cups/2.4.19"` → 三个依赖均已发布，
> 版本号未被占用（exit 0）。

## 编译步骤

1. `python3 scripts/ohc-run.py init-build ayatana-indicator-printers 23.10.1 --url=...`
   （源码 SHA256 `f622b831ea6e90d7fc3240f3322cba1a260d8f2490878f0a82c554aa58c2b0d4`）
2. `lang-preflight`：task=cpp / detected=c → 兼容族，继续（C 项目按 CMake 构建）
3. 源码适配（编辑 `$BUILD_SRC_DIR` 后 `refresh-patch --auto` 生成 2 个补丁）
4. 手写 `conanfile.py`（CMake + PkgConfigDeps）、`test_package/`
5. `conan create .`（真实构建 + 上游测试 + 包内测试）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ERROR: Version conflict: zlib/1.3.1.1 vs zlib/1.3.1.1.1.1`（Conflict originates from cups/2.4.19） | `cups/2.4.19` 要求 `zlib/1.3.1.1`，`glib/2.88.0.1` 要求 `zlib/1.3.1.1.1.1` | 改用同一 track 的 `glib/2.84.0.1` + `ayatana-common/0.9.11` |
| 2 | CMake configure: `No package 'gio-unix-2.0' found` | glib 配方 `cpp_info` 未声明 `gio-unix-2.0` 组件，PkgConfigDeps 不生成该 `.pc` | `generate()` 中从 glib 包内复制 `lib/pkgconfig/gio-unix-2.0.pc` 并改写 `prefix=/` 为包路径 |
| 3 | `find_program(cups-config)` 拿到 cups 包的脚本，但 `CUPS_CFLAGS` 为空、`-L` 缺失 → `cups/cups.h` 找不到、`-lcups` 找不到 | cups-config 报告构建期前缀（`prefix=/`、`includedir=/usr/include`、`libdir=/lib`），与可重定位包布局不符 | 0001 补丁改用 `pkg_check_modules(CUPS REQUIRED cups>=2.4)`，并把 `CUPS_INCLUDE_DIRS`/`CUPS_LIBRARY_DIRS`/`CUPS_LIBRARIES` 合入 `SERVICE_*` |
| 4 | `make` 报 `/bin/sh: /data/service/hnp/bin/gdbus-codegen: No such file or directory`（Error 126） | SDK 的 `gdbus-codegen` 是悬空符号链接（`../glib.org/glib_2.38.2/bin/gdbus-codegen`），`find_program` 先命中它 | `CMakeToolchain` 设置 `CMAKE_PROGRAM_PATH`（glib 包 `bin` 优先），钉死可用工具 |
| 5 | `ld.lld: unable to find library -lglib-2.0/-lgio-2.0/-layatana-common/-lcups` | `pkg_check_modules` 把 `-L` 放在 `*_LIBRARY_DIRS`，上游只用 `*_LIBRARIES`（Linux 上依赖在系统默认搜索路径，OHOS 包布局不在） | 0001 补丁增加 `link_directories(${SERVICE_LIBRARY_DIRS} ${CUPS_LIBRARY_DIRS})` |
| 6 | `find_package(Intltool REQUIRED)` 配置失败（po/ 子目录） | `Intltool` CMake 模块来自 Ubuntu `cmake-extras`，OHOS 无 | 0001 补丁改为 `find_package(Intltool QUIET)`，未找到时不加入 `po/` |
| 7 | 可执行文件链接残留 `g_libintl_*` 未定义符号 | `main.c` 使用 `<glib/gi18n.h>`，`g_libintl_*` 由 glib 包内 `libintl.so` 提供，但 PkgConfigDeps 生成的 `glib-2.0.pc` 缺 `-lintl` | `generate()` 给 `glib-2.0.pc`/`gio-2.0.pc`/`gobject-2.0.pc` 的 `Libs:` 行追加 `-lintl` |
| 8 | 直接运行守护进程 `rc=133`（SIGTRAP）：`ERROR **: Error creating cups notify handler: Could not connect: No such file or directory` | `indicator_printers_service_init()` 里 `cups_notifier_proxy_new_for_bus_sync(G_BUS_TYPE_SYSTEM, ...)` 失败即 `g_error()` 致命退出 | 属上游设计：必须提供系统总线。测试用私有 system 总线（见「验证结果」） |
| 9 | 私有总线起不来：`Failed to bind socket ...: Operation not permitted` | 鸿蒙沙箱仅允许在 `/data/storage/el2/base/cache` 内 bind AF_UNIX socket | 测试总线改用 TCP transport（`tcp:host=127.0.0.1,port=0` + `ANONYMOUS` 认证） |

## 源码修改（补丁）

| 补丁 | 修改内容 |
|------|----------|
| `patches/0001-CMakeLists.txt.patch` | `CMakeLists.txt`：① CUPS 由 `cups-config` 改为 `pkg_check_modules(CUPS REQUIRED cups>=2.4)`，补 `CUPS_INCLUDE_DIRS`/`CUPS_LIBRARY_DIRS`/`CUPS_LIBRARIES`；② 增加 `link_directories(${SERVICE_LIBRARY_DIRS} ${CUPS_LIBRARY_DIRS})`；③ `po/` 的 `find_package(Intltool QUIET)` 可选化 |
| `patches/0002-data-CMakeLists.txt.patch` | `data/CMakeLists.txt`：`.desktop` 安装目标由硬编码 `/etc/xdg/autostart` 改为 `${CMAKE_INSTALL_FULL_SYSCONFDIR}/xdg/autostart` |

> 补丁中无平台宏（无 `__OHOS__`），未修改任何 `src/` 源码；守护进程行为与上游一致。

## 上游测试（R51 三步法）

### 1. 清点

上游测试集中在 `test/`：

- `test/CMakeLists.txt`：`add_test(mock-cups-notifier mock-cups-notifier)` —— 唯一注册测试
  （`ENABLE_TESTS=ON` 时进入构建；上游默认 OFF）。
- `test/mock-cups-notifier.c`：GDBus 模拟 CUPS 通知服务，导出
  `/org/cups/cupsd/Notifier` 并发出 `PrinterStateChanged`；无系统总线时提前退出，**退出码 0**。
- 另有两个非 CTest 目标（不计入用例数）：`cppcheck` 自定义目标（静态分析）与
  `ENABLE_COVERAGE` 分支（依赖 Ubuntu `CoverageReport` 模块）。

**用例总数：1**（`ctest -N` 输出见下）。

### 2. 实际执行

配方 `ENABLE_TESTS=ON`，在 `build()` 内构建后执行上游 CTest：

```bash
ctest --output-on-failure
Test project /storage/Users/currentUser/.conan2/p/b/ayata2e04c80ea3a7f/b/build/Release
    Start 1: mock-cups-notifier
1/1 Test #1: mock-cups-notifier ...............   Passed    0.06 sec

100% tests passed, 0 tests failed out of 1
```

- 用例总数：1；通过：1；失败：0；跳过：0
- 用例名称：`mock-cups-notifier`
- 日志路径：`reports/conan-create.log`（`conan create` 完整日志，含上述 CTest 输出）

> 未修改任何上游测试用例；上游测试在 conan create 中随构建实际执行。

### 3. 鸿蒙特有测试（`test_package/`，新增，全部为运行时行为验证）

`test_package/test.sh` + `test_package/ohos-dbus-check.c`：以 `dbus` 包提供的
`dbus-daemon` 启动私有 system/session 总线（TCP + ANONYMOUS），运行**安装后的**
守护进程并观察其运行时行为：

1. 安装产物完整（指示器描述文件 + autostart `.desktop`）；
2. 守护进程为可执行 ELF（打包时已用 `binary-sign-tool` 签名——鸿蒙只执行已签名 ELF）；
3. 守护进程连接 system 总线、占用 `org.ayatana.indicator.printers`，并在
   `/org/ayatana/indicator/printers` 导出 `org.gtk.Actions`、
   `/org/ayatana/indicator/printers/desktop` 导出 `org.gtk.Menus`；
4. 扮演 `org.cups.cupsd.Notifier` 的对端发出 `PrinterStateChanged` 后，守护进程仍存活
   且指示器接口保持导出。

## 验证结果

```bash
# 1) 依赖预检（W0）
bash ci/scripts/preflight_check.sh ayatana-indicator-printers/23.10.1 \
    --deps "glib/2.84.0.1 ayatana-common/0.9.11 cups/2.4.19"     # exit 0

# 2) 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight ayatana-indicator-printers 23.10.1 --src $BUILD_SRC_DIR
# → 语言匹配: task=cpp, detected=c，继续适配主流程

# 3) conan create（真实构建 + 上游测试 + 包内测试）
conan create . --version=23.10.1 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=ayatana-indicator-printers/23.10.1
# → 1/1 Test #1: mock-cups-notifier Passed（上游）
# → test.sh: ALL TESTS PASSED（鸿蒙特有 D-Bus 测试）
# → exit 0   日志：reports/conan-create.log
```

包内产物（`conan create` 实测）：

```
libexec/ayatana-indicator-printers/ayatana-indicator-printers-service   # 守护进程（已签名）
etc/xdg/autostart/ayatana-indicator-printers.desktop
share/ayatana/indicators/org.ayatana.indicator.printers
licenses/COPYING
```

test_package 关键输出：

```
[test 1] installed data artifacts → OK
[test 2] daemon binary → OK
[test 3] daemon on private D-Bus buses
  [probe] NameHasOwner(org.ayatana.indicator.printers) = true
  [probe] /org/ayatana/indicator/printers exports org.gtk.Actions
  [probe] /org/ayatana/indicator/printers/desktop exports org.gtk.Menus
[test 4] CUPS PrinterStateChanged signal
  [notify] claimed org.cups.cupsd.Notifier as :1.1
  [notify] emitted org.cups.cupsd.Notifier.PrinterStateChanged
  → daemon survived, indicator still exported
ALL TESTS PASSED
```

## 注意事项

- 非致命告警（保留上游行为，未处理）：`main.c` 的 `-Wdeprecated-non-prototype`
  与 `cmake_minimum_required` 位于 `project()` 之后的 CMake dev 告警。
- `systemd` 未安装（无 `systemd.pc`），上游 `data/CMakeLists.txt` 因此跳过
  `ayatana-indicator-printers.service` 安装；`/etc/xdg/autostart` 的 `.desktop`
  仍会安装（改为包内相对前缀）。
- 守护进程依赖系统总线创建一个 CUPS 通知代理；在无系统总线的环境中启动会
  以 `g_error()` 终止（`rc=133`），这是上游行为，不是打包缺陷。
---

**编译结束**: 2026-10-16 14:35
**最终状态**: built
