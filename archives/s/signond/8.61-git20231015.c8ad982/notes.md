# signond 8.61-git20231015.c8ad982 适配笔记

## 编译环境
- 构建系统: cmake（上游为 qmake 工程 `signon.pro` + `*.pri`；配方经 `exports_sources` 自带 `CMakeLists.txt` 及 `*.pc.in` / `*.service.in` 模板）
- 编译日期: 2026-10-16
- 编译器: clang / clang++（OHOS SDK 26.0.0.18 / clang 15，aarch64-linux-ohos）
- 状态: built

## 适配背景

signond 是 accounts-sso 的 SSO 守护进程（D-Bus 服务 `com.google.code.AccountsSSO.SingleSignOn`），
是 `kaccounts-integration` / `kaccounts-providers` 依赖链的最深缺口：

```
kaccounts-providers 26.04.0
  └─ kaccounts-integration 26.04.0（KAccounts6）
       ├─ SignOnQt6 >= 8.55  -> libsignon-qt 8.61        [已发布]
       └─ signond（守护进程 + 认证插件）                 [本包]
```

上游 `VERSION_8.61`（2022-03-09）之后的 master 才具备 Qt6 支持，平台因此固定 master 快照
commit `c8ad982`（"Port away from deprecated QProcess signal"，2023-11-24）。

> 版本号说明：`8.61-git20231015.c8ad982` 是按平台任务卡给定的版本名（沿用本仓 `X.Y.Z-gitYYYYMMDD.<short-sha>`
> 命名），其中固定 commit `c8ad982` 的实际提交日期为 **2023-11-24**（GitLab API `created_at` 与归档内文件 mtime
> 一致）；名称中的日期为平台侧给定的快照标识，不代表 commit 日期。

本包只构建守护进程侧（`lib/plugins`、`lib/signond`、`src/`）；客户端库 `lib/SignOn`
（`SignOnQt6`）已作为独立包 `libsignon-qt/8.61` 发布，重复构建会与其产物冲突。

## 编译步骤

```bash
# 1) 上游只有 qmake；ohpcd qtbase 无 OHOS mkspec，故用自写 CMakeLists.txt 复刻 qmake 目标
#    （随配方 exports_sources 分发，与源码树同级）

# 2) 依赖：守护进程 QT += sql，ohpcd 的 qtbase 是 FEATURE_sql=OFF => 改用已发布的
#    qtbase-sql-dbus/6.11.1（含 Qt6Sql 与 plugins/sqldrivers/libqsqlite.so）
conan install --requires=qtbase-sql-dbus/6.11.1 -r=ohpcd \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    -g CMakeToolchain -g CMakeDeps -of .

# 3) 配置 / 构建（qtbase-sql-dbus 的 cpp_info 为 cmake_find_mode=none，须显式给 Qt6_DIR）
QT6=<qtbase-sql-dbus 包目录>/lib/cmake/Qt6
cmake -S <src> -B <bld> -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=<stage> \
    -DQt6_DIR=$QT6 -DCMAKE_PREFIX_PATH=<qtbase-sql-dbus 包目录> \
    -DBUILD_SHARED_LIBS=ON -DSIGNOND_BUILD_UPSTREAM_TESTS=ON
cmake --build <bld> -j1 && cmake --install <bld>

# 4) 上游可运行测试（不依赖会话总线的那一套）
LD_LIBRARY_PATH=<依赖 lib 目录>:<bld> ctest --output-on-failure

# 5) 配方验证（8 门禁，G2 内含 conan create + test_package）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify signond 8.61-git20231015.c8ad982
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游仅 qmake 工程，ohpcd qtbase 无 OHOS mkspec，无法直接 qmake 交叉编译 | qtbase 包未提供鸿蒙 mkspec | 自写 `CMakeLists.txt` 按需复刻 `signon.pro` / `lib/plugins/*.pro` / `lib/signond/SignOn/SignOnExtension.pro` / `src/**/*.pro` / `plugins.pri` 的目标、include、DEFINES 与安装语义（**安装规则的非等同项见下面「偏差清单」**），经 `exports_sources` 随配方分发 |
| 2 | 守护进程需要 `Qt6Sql`，但 ohpcd `qtbase/6.11.1.1` 以 `FEATURE_sql=OFF` 构建（无 `libQt6Sql.so`、无 `lib/cmake/Qt6Sql`、无 `sqldrivers/`） | qtbase 未构建 SQL 模块 | 依赖改为已发布的 `qtbase-sql-dbus/6.11.1`（提供 Core/Gui/Widgets/Network/Sql/DBus/Xml + `plugins/sqldrivers/libqsqlite.so`；ktextaddons 2.0.2 / akonadi 25.12.3 / qmmp 2.3.2 先例） |
| 3 | `find_package(Qt6 COMPONENTS Sql ...)` 失败：CMakeDeps 未生成 Qt6 配置 | qtbase-sql-dbus 根 `cpp_info` 为 `cmake_find_mode=none`，CMakeDeps 直接跳过 | 配方 `generate()` 把 `<pkg>/lib/cmake/Qt6` 写入 `Qt6_DIR` 缓存变量（libsignon-qt 8.61 同款） |
| 4 | 插件进程报 `Failed to load libpasswordplugin.so: symbol not found: _ZN19AuthPluginInterface11qt_metacastEPKc` | `lib/plugins/signon-plugins.pro` 是 `TEMPLATE=lib` + 仅 `HEADERS`：qmake 对 `SignOn/authpluginif.h` 跑 moc，`AuthPluginInterface` 的 `qt_metacast`/`qt_metacall`/`staticMetaObject`/虚表都由 `libsignon-plugins.so` 承载；CMake AUTOMOC 只扫描 target sources、不跟随 `#include`，初版因此产出了空壳库 | `add_library(signon-plugins ...)` 显式把 `SignOn/authpluginif.h`（及 `uisessiondata.h`/`uisessiondata_priv.h`）列为 target source，AUTOMOC 便生成并编译 `moc_authpluginif.cpp` |
| 5 | 插件文件名不匹配，插件宿主找不到插件 | qmake `CONFIG+=plugin` 产出 `lib<type>plugin.so`，宿主按 `SIGNON_PLUGIN_PREFIX("lib") + type + SIGNON_PLUGIN_SUFFIX("plugin.so")` 拼路径；初版 CMake 设了 `PREFIX ""` 产出 `passwordplugin.so` | `set_target_properties(... PREFIX "lib")` |
| 6 | 上游测试 `signon-passwordplugin-tests` 链接报 `undefined symbol: vtable for PasswordPluginNS::PasswordPlugin` | 测试 `#include "passwordplugin.cpp"`，qmake 通过 `HEADERS += passwordplugin.h` 跑 moc；CMake 侧该头不在 target sources | 把 `<src>/plugins/password/passwordplugin.h` 也列为该测试 target 的 source |
| 7 | 守护进程在无 D-Bus 会话总线的环境里静默 `SIGABRT`（退出 134），看不到原因 | 守护进程默认把日志交给 `syslog`（`SignonTrace` 安装的自定义 message handler），stderr 无输出 | 设 `SSO_LOGGING_OUTPUT=stdout` 让日志回到 stderr，确认其停在 `qFatal("SignonDaemon requires DBus to start working")`；平台缺的是总线本身（无 `dbus-daemon`，可写挂载点 `bind(2)` Unix socket EPERM），不是配方缺陷 |
| 8 | `make -j2` 报 `jobserver mkfifo: Operation not permitted` | 工作目录为 FUSE/HMDFS 挂载，禁 `mkfifo` | 统一 `-j1` 构建 |
| 9 | `lib/signond/interfaces/*.xml` 缺失 | 该目录是 git submodule（`signon-dbus-specification`），GitLab commit 归档不含子模块内容 | CMake 改为按 glob 条件安装（当前树中为空即不安装）；守护进程的 D-Bus 适配器代码是仓库自带并编译进 ELF 的，运行不受影响 |
| 10 | `signond.pro` 把不存在的 `setupstorage.sh` 列入 `OTHER_FILES`/`conf_file`（上游 `make install` 实际会失败） | 上游仓库漏文件 | CMake 只安装真实存在的 `signond.conf`，不复制这条破损的安装项 |
| 11 | W3 本地 CI 的 L5a 质量门禁报 3 个库「缺少 DT_SONAME」 | 上游 qmake 从不设 `VERSION`，故上游 `.so` 无 SONAME；本平台对 CMake 而言是未知系统（`CMAKE_SYSTEM_NAME=HarmonyOS` 无 Platform 模块），`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 为空，CMake 的 `VERSION`/`SOVERSION` 属性也**不会**产生 `-soname`，于是 CMake 侧同样没有 SONAME | 用显式链接选项补上相对 SONAME：`target_link_options(<t> PRIVATE "LINKER:-soname,libsignon-plugins.so")`（三个 SDK 库各一条，未版本化命名与上游安装名一致）；并在 test_package 中用 `readelf -d` 断言 SONAME 存在。修复后 L5a 0 error |
| 12 | 插件 SDK 头文件不自洽：`authpluginif.h`/`uisessiondata.h` 需要 `<SignOn/sessiondata.h>`、`<SignOn/signonerror.h>`、`<SignOn/SessionData>` | 上游同一源码树里这些客户端类型头由 `lib/SignOn` 提供，本仓拆成 `signond` + `libsignon-qt` 两个包 | 把 SDK 头实际需要的 4 个客户端头（`sessiondata.h`/`signonerror.h`/`libsignoncommon.h`/`SessionData`，来自同一源码树同一版本）一并安装到 `include/signon-plugins/SignOn`，使 `signon-plugins.pc` 自洽（去掉悬空的 `Requires: libsignon-qt6`）；不在 recipe 里 `requires(libsignon-qt)`，否则会把另一个 Qt6 提供方（plain `qtbase`）拉进依赖图与 `qtbase-sql-dbus` 冲突。test_package CASE E 通过 `QLibrary` + `auth_plugin_instance` 真实加载插件，验证包含这些头的 SDK 可独立编译使用 |

## 源码修改

无补丁。`patches/` 为空、`patches_applied: []`。配方通过 `exports_sources` 额外分发 7 个自写构建文件
（属配方资产，非上游源码改动）：

1. `CMakeLists.txt` — 复刻 qmake 的 daemon / pluginprocess / plugins / SDK 目标与 INSTALLS 语义（Qt6 形态）
2. `signond.pc.in`、3. `signon-plugins.pc.in`、4. `signon-plugins-common.pc.in`、5. `SignOnExtension.pc.in`
   — 由上游 `*.pc.in`（`$$VAR` qmake 语法）改写为 CMake `@VAR@` 形态
6. `com.google.code.AccountsSSO.SingleSignOn.service.in`、7. `com.nokia.SingleSignOn.Backup.service.in`
   — 同上；`Exec` 用稳定部署前缀（默认 `/usr/bin`，可 `-DSIGNOND_DBUS_EXEC_BINDIR=` 覆盖），
   避免把 conan 私有构建缓存路径写进产物

### 与上游 qmake 安装规则的偏差清单（按需复刻，非逐条等同）

| 项 | 上游 qmake | 本适配 | 原因 |
|---|---|---|---|
| `SignOn/ipc.h` | `signon-plugins-common.pro` 的 `headers.files` 只装 `blobiohandler.h` | 一并安装 `ipc.h` | 它是 daemon↔插件协议契约的一部分（`BlobIOHandler` 与 `ipc.h` 的 opcode 必须同版本），且 test_package 依赖它做端到端驱动 |
| 插件私有头 | `plugins.pri` 的 `headers.path=include/signon-plugins` 会把 `passwordplugin.h`/`exampleplugin.h`/`exampledata.h` 装上 | 未安装 | 这三个是各插件的**实现**头（非稳定 SDK 接口）；示例源码已按上游装到 `share/doc/signon-plugins-dev/example/` |
| `signond.conf` | `conf_file.path = /etc/`（绝对路径，会写宿主 `/etc`） | 安装到包内 `share/signond/signond.conf` | conan 包不应写入宿主 `/etc`；守护进程按 `QSettings` SystemScope 读 `/etc/signond.conf`，可用 `SSO_CONFIG_FILE_DIR` 覆盖，部署时从包内 `share/signond/` 复制过去即可 |
| `src/plugins/test`（ssotest/ssotest2 测试插件） | `src/plugins/plugins.pro` 的 SUBDIRS 含 `test` | 未构建 | 它们是上游测试专用插件，只被依赖会话总线的 `tests/signond-tests` 使用（该套件在本环境不可运行） |
| SDK 客户端类型头（`sessiondata.h` 等 4 个） | 由同一源码树的 `lib/SignOn` 安装到 `include/signon-qt6/SignOn` | 额外装一份到 `include/signon-plugins/SignOn` | 本仓把源码树拆成 `signond` + `libsignon-qt` 两个包；插件 SDK 头引用这些类型，装到这里才能让 `signon-plugins.pc` 自洽（同一源码树、同一版本，无版本分叉） |
| `setupstorage.sh` | 列入 `OTHER_FILES`/`conf_file` 但仓库中不存在（上游 `make install` 会失败） | 不安装 | 上游漏文件 |

## 依赖版本

- `qtbase-sql-dbus/6.11.1`（ohpcd 已发布；提供 Qt6 Core/DBus/Sql/Xml/Network + SQLite 驱动插件，
  Qt6 CMake 包位于包内 `lib/cmake/Qt6`）
- 客户端**库** `SignOnQt6`（`SignOn::Identity`/`AuthSession` 等，链接用）由独立包 `libsignon-qt/8.61` 提供；
  插件 **SDK** 所需的客户端类型头（`sessiondata.h`/`signonerror.h`/`libsignoncommon.h`/`SessionData`）已随本包安装，
  插件开发方无需额外依赖（见「偏差清单」与本文件第 3 条注意事项）

## 验证结果

```bash
# 上游测试（build() 内实跑，tests/passwordplugintest）
$ ctest --output-on-failure
    Start 1: signon-passwordplugin-tests
1/1 Test #1: signon-passwordplugin-tests ...... Passed
100% tests passed, 0 tests failed out of 1
Totals: 9 passed, 0 failed, 0 skipped, 0 blacklisted

# 配方验证（G0-G4 + L2/L4/L5）
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify signond 8.61-git20231015.c8ad982
Verdict: PASS

# 本地 CI 模拟（W3）：修复 SONAME 后真实结果
$ python3 $SKILL_ROOT/scripts/ohc-run.py finish signond 8.61-git20231015.c8ad982 built
  ✅ 本地 CI 模拟通过
  L1a/L1b/L1c = ok（conan create 实跑 + 上游 ctest 实跑）
  L1e         = ok（破坏性反向验证：移走 bin/lib/include 后 test_package 确实失败）
  L4          = pass（无补丁）
  L5          = pass（修复前 L5a 报 3 个库缺 DT_SONAME；补 `LINKER:-soname` 后 0 error）
  L2          = skip（signond/signonpluginprocess 无 --version/--help，非阻塞）

# test_package（五组用例，详见 reports/test-report.md）
CASE 1 真实 bin/signond 启动 -> 停在会话总线探测（qFatal，EXIT=134）
CASE 2 signonpluginprocess + libpasswordplugin.so 两条认证流程全通过
CASE 3 产物契约 + SONAME + ELF DT_NEEDED/RUNPATH 无 conan 缓存路径
CASE E QLibrary + auth_plugin_instance 进程内加载插件，验证 SDK 头自洽
TOTAL pass=22 fail=0（consumer.cpp）+ test_package Python 侧 16 项
```

## 注意事项

1. **D-Bus 会话总线是运行前提**：环境内无 `dbus-daemon` 且可写挂载点 `bind(2)` Unix socket 返回
   `EPERM`，故守护进程实测停在 `SignonDaemon requires DBus to start working`（退出码 134）。
   这是平台环境缺口而非配方缺陷；接入可用会话总线后无需重编译。
2. **`SSO_PLUGINS_DIR` / `SSO_EXTENSIONS_DIR` 可覆盖**插件/扩展目录（编译期默认 `/usr/lib/signon`），
   `SSO_STORAGE_PATH` 覆盖凭据库目录，`SSO_LOGGING_OUTPUT=stdout` 把日志从 syslog 切到 stderr。
3. **插件 SDK 自洽**：`include/signon-plugins/SignOn/` 已包含 SDK 头所需客户端类型
   （`sessiondata.h`/`signonerror.h`/`libsignoncommon.h`/`SessionData`），`pkg-config --cflags signon-plugins`
   即可编译第三方插件；客户端**库**（`SignOnQt6`，链接用）仍在独立包 `libsignon-qt`。
4. 本包未启用上游的可选特性：`enable-backup`、`enable-p2p`、`cryptsetup` 扩展、`HAVE_LIBPROXY`。
5. `bin/signond` 与 `bin/signonpluginprocess` 是守护进程与插件宿主，属系统级服务；
   安装到非 `/usr` 前缀时需同步改写 `share/dbus-1/services/*.service` 的 `Exec`。
6. 三个 SDK 库带**未版本化** SONAME（`libsignon-plugins.so` 等）。原因是本平台对 CMake 而言是未知系统
   （`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 为空），CMake 的 `VERSION`/`SOVERSION` 不产生 `-soname`；
   显式补的 SONAME 与上游安装名一致，故 daemon/插件在运行期仍以裸名解析，不引入 `libX.so.0` 缺失风险。
7. 守护进程真正的 D-Bus 功能面（服务注册、`AuthService`/`Identity`/`AuthSession` 接口）在无会话总线的
   环境里**无法验证**；本包只验证到「全量初始化后停在总线探测」这一步（CASE 1 已在报告中标明范围）。
---

**编译结束**: 2026-10-16 01:25
**最终状态**: built
