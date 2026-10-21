# modemmanager-qt 6.28.0 适配笔记

## 编译环境
- **类型**: C++/CMake 共享库（KDE Frameworks 6 - ModemManagerQt，libKF6ModemManagerQt.so）
- **编译日期**: 2026-10-18
- **编译器**: clang（OHOS SDK 26.0.0.18 随附工具链），C++20
- **平台**: arm64-ohos（ohos-aarch64-full profile）
- **状态**: built（conan-verify 门禁结果见 reports/conan-verify-report.md）

## 源码（source()）
`get()` 下载 KDE Frameworks 官方 tarball 并 `strip_root=True` 解压：

- URL: `https://download.kde.org/stable/frameworks/6.28/modemmanager-qt-6.28.0.tar.xz`
- sha256: `742891c3c1dfcd6c9eaa2b1664cfe7e9b311187eec7ecd9d8812829dce8485c9`

## 适配决策
1. **KF_IGNORE_PLATFORM_CHECK=TRUE** — OHOS 不在 KDE 平台列表中（kconfig / kcoreaddons 先例）。
2. **ModemManager.pc 生成** — 依赖包 modemmanager/1.24.2 自带的 `ModemManager.pc` 位于其包目录内，
   不在默认 pkg-config 搜索路径，且 `Cflags` 只含 `-I${includedir}/ModemManager`（上游源码按
   `<ModemManager/ModemManager.h>` 包含，还需 `-I${includedir}`）；上游 `cmake/FindModemManager.cmake`
   通过 `PKG_SEARCH_MODULE(MODEMMANAGER ModemManager)` 解析，因此 `generate()` 在 generators 目录
   重新写出一份 `ModemManager.pc`（`Cflags` 同时包含 `include` 与 `include/ModemManager`），并把
   generators 前置到 `PKG_CONFIG_PATH`。不修改上游查找逻辑。
3. **Qt6 Core/DBus/Xml** — 上游 `find_package(Qt6 6.9.0 COMPONENTS Core DBus Xml REQUIRED)`；qtbase/6.11.1.1
   已发布。qtbase 的 CMakeDeps 配置不完整，配方生成 `conan_cmakedeps_paths.cmake` 手动前置
   `lib/cmake`、`lib`、`include` 三类路径（kdbusaddons 先例）。
4. **ECM 基线** — 上游要求 ECM >= 6.28.0；注册表无 ecm/6.28.0，采用 extra-cmake-modules/6.29.0，
   并手动设置 `ECM_MODULE_PATH`（CMakeDeps 生成的 ECMConfig.cmake 不传播该变量）。
5. **C++20** — `CMAKE_CXX_STANDARD=20` 并追加 `CMAKE_CXX_FLAGS=-std=c++20`，避免上游
   variable_watch 覆盖后落到默认标准（kcoreaddons 先例）。
6. **DT_SONAME 注入** — CMake 无 Platform/HarmonyOS 模块时 lld 不写 DT_SONAME；经
   `CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX` 规则文件注入
   `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG/CXX_FLAG=-Wl,-soname,`，并置
   `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`，产出裸 SONAME 单文件（kservice/kcoreaddons 先例）。
7. **BUILD_TESTING=ON** — 上游 autotests 全量构建并以 ctest 运行（`--no-tests=error --timeout 120`），
   测试程序链接 `KF6ModemManagerQt_static`（`-DMMQT_STATIC=1`），因此在测试态使用**会话总线**。
   私有总线由 build 依赖 `dbus/1.14.10.3` 提供（该修订保留共享客户端库，同时打包 dbus-daemon）。

## 私有会话总线与账户数据库 shim（OHOS 关键差异）
- 设备构建环境为应用沙箱：`/data/storage/el2/base`（tmpfs）允许 AF_UNIX bind，HMDFS 用户卷返回
  EPERM，因此启动总线前用 `bind(2)` 探测目录。
- 沙箱 UID/GID 20020084 **没有** `/etc/passwd`、`/etc/group` 条目（系统 passwd 只含服务账户）。
  `dbus-daemon` 在接受 EXTERNAL 客户端时执行
  `bus_policy_allow_unix_user() -> _dbus_unix_groups_from_uid() -> fill_user_info()`，
  musl 的 `getpwuid_r()` 查询失败后直接判定
  `Did not get any groups for UID 20020084`，在 Hello 之前断开连接
  （verbose 日志：`dbus-transport.c(573): Client UID ... was rejected, disconnecting`）。
- dbus/1.14.10.2 的既有验证走 TCP + `<auth>ANONYMOUS</auth><allow_anonymous/>`；QtDBus 只实现
  EXTERNAL，不能沿用该等价路径。配方保留 `unix` + `EXTERNAL`，在测试期以 `LD_PRELOAD` 加载一个
  只对当前 UID 生效的账户 shim（`getpwuid_r` / `getpwnam_r` / `getgrouplist`），给 dbus-daemon
  提供合成账户视图。系统文件只读，不写入任何 passwd/group 条目；shim 编译后校验 ELF 为 AArch64
  再使用。shim 对其余 UID 返回“未找到”（测试期只校验本进程客户端，不需要服务账户身份映射），
  因此不会读取真实 `/etc/passwd` 中的服务账户条目。
- 该 shim 只服务于构建期测试（上游 autotest 与 test_package 各编译一次，位于各自 build 目录），
  不进入发布包。

## Qt6DBus 与 libdbus（OHOS 运行期关键差异）
- `libQt6DBus.so.6` 的 NEEDED 只有 `libQt6Core.so.6 / libc++_shared.so / libc.so`：
  Qt6DBus 用 `QLibrary` 在运行期 `dlopen("libdbus-1.so.3")`，不写入 NEEDED。
- 库不存在时 `QDBusConnection::sessionBus()` 返回未连接，`call()` 报
  `org.freedesktop.DBus.Error.Disconnected: Not connected to D-Bus server`，且私有总线
  daemon 侧连 `AUTH EXTERNAL` 都看不到（客户端没有发起 socket 连接）。
- dbus 配方 1.14.10/.1/.2 把客户端库钉成 STATIC（只有 `.a`），只有 1.14.10.3 保留共享库并
  打包 `libdbus-1.so.3` 及其 SONAME 链接（该修订正是为此建立）。因此 build 工具依赖选用
  `dbus/1.14.10.3`，并把该包 `lib/` 前置到测试进程的 `LD_LIBRARY_PATH`；daemon 自身也动态
  链接 libdbus，启动 env 同样需要该路径。

## 安装期 RPATH 重写与 OHOS 用户卷执行限制
- CMake 默认给构建树共享库写入 DT_RUNPATH（指向 qtbase 包内 `lib/`），安装步骤再把它
  重写：原字符串就地清零、`.dynamic` 中的 RUNPATH 条目删除（实测两处共 181 字节差异，
  `readelf -d` 其余条目一致）。
- 实测（同机、同依赖、同 LD_LIBRARY_PATH）：
  - 构建树原始库 → `dlopen()` OK；
  - 安装后重写过的库 → `Error loading shared library ...: Permission denied`（EACCES），
    即便把 libQt6Core/libQt6DBus/libQt6Xml 全部预加载仍失败，ELF 结构完好；
  - 用 `cat` 生成的两份新文件（一份取构建树内容、一份取安装后内容）结果不变——
    取决于 ELF 内容，与文件属主/权限/xattr/创建方式无关；
  - 对照 kservice/6.28.0：其库本就没有 RUNPATH，安装步骤无字节可改，包内文件与构建
    产物 sha256 相同且可正常加载。
- 修复：`CMAKE_SKIP_RPATH=TRUE`，链接器不写任何 RPATH，安装步骤没有可重写的内容，
  包内库与链接器输出逐字节一致。已在设备上以临时安装前缀实测：构建库与安装库 sha256
  相同（`5d954ba2…`），两者 `dlopen()` 均 OK。依赖由 `LD_LIBRARY_PATH` 解析。

## 上游测试清点（实测非推断）
- `BUILD_TESTING=ON` + ctest 全量运行 10 个 CTest 程序、11 个 QTest 用例函数：
  **10/10 通过（100%）**
- `modemomapropertiestest` 由上游按 `MODEMMANAGER_VERSION >= 1.2.0` 条件注册（modemmanager/1.24.2 满足）。

## 消费者测试（test_package）
- 共享库消费者：`find_package(KF6ModemManagerQt)` 链接 `KF6::ModemManagerQt`，12 个校验点覆盖
  notifier 单例、modemDevices 空列表、Modem/Sim/Bearer 的 `uni()` 往返、`Sms` 在无服务时的
  路径语义（见下）、`Modem::isValid()`、系统总线连通性，以及注册/释放
  `org.freedesktop.ModemManager1` 触发的 `serviceAppeared` / `serviceDisappeared`
  （`DBUS_SYSTEM_BUS_ADDRESS` 指向同一私有总线）。
- `Sms::uni()` 的上游语义与 Sim/Bearer 不同：`SmsPrivate` 仅在生成接口
  `OrgFreedesktopModemManager1SmsInterface::isValid()` 为真时缓存路径，而该接口的
  `QDBusAbstractInterface` 构造会向远端对象发起一次调用——服务名不存在时报
  `ServiceUnknown`、仅注册服务名而无对象时报 `UnknownObject`，两种情况 `isValid()` 均为假。
  因此消费者测试断言“无 ModemManager 服务时 `Sms::uni()` 为空”；上游 autotest 用 fake bus
  提供了真实对象，`Sms` 在那里走有效分支。
- 结果：**12/12 通过（100%）**

## 平台限制（真实记录）
- 沙箱无 passwd/group 条目：会话总线需测试期 shim（上述），不影响发布库行为。
- HMDFS 用户卷不支持 AF_UNIX bind：总线 socket 必须落在 el2 沙箱 tmpfs。
