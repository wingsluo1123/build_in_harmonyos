# signond

`signond`（Single Sign On daemon）是 [accounts-sso](https://gitlab.com/accounts-sso) 的在线账号认证守护进程：
它以 D-Bus 服务 `com.google.code.AccountsSSO.SingleSignOn` 的形式对外提供凭据存储与 SSO 认证能力
（`AuthService` / `Identity` / `AuthSession` 三组 D-Bus 接口），并通过**认证插件**完成具体服务商
（密码、OAuth、SASL 等）的登录会话。KDE 的 `kaccounts-integration` / `kaccounts-providers`
即建立在它之上。

- 上游仓库: https://gitlab.com/accounts-sso/signond
- 上游版本: `8.61-git20231015.c8ad982`（`VERSION_8.61` 之后的 master 快照，commit `c8ad982`）
- 许可证: LGPL-2.1-or-later
- 构建系统: 上游 qmake（本适配经 `exports_sources` 自带 `CMakeLists.txt`，CMake + Qt6）

## 功能概述

本包交付 signond 源码树的**守护进程侧**：

| 组件 | 产物 | 说明 |
|---|---|---|
| `src/signond` | `bin/signond` | 守护进程：凭据库（Qt SQL / SQLite）、D-Bus 接口、会话与插件调度 |
| `src/remotepluginprocess` | `bin/signonpluginprocess` | 插件宿主进程：由守护进程按需拉起，用 blob IPC 协议驱动认证插件 |
| `src/plugins/password` | `lib/signon/libpasswordplugin.so` | 上游 `password` 认证插件（用户名/密码、UI 回问） |
| `src/plugins/example` | `lib/signon/libexampleplugin.so` | 上游示例插件（插件开发模板） |
| `lib/plugins/signon-plugins` | `lib/libsignon-plugins.so` | **插件 SDK**：`AuthPluginInterface` 元对象/虚表 + 公开头 + `signon-plugins.pc` |
| `lib/plugins/signon-plugins-common` | `lib/libsignon-plugins-common.so` | 守护进程↔插件进程的 blob IPC 序列化（`BlobIOHandler` / `ipc.h`） |
| `lib/signond/SignOn` | `lib/libsignon-extension.so` | **扩展 SDK**：访问控制/密钥/密文存储/密钥授权扩展接口 + `SignOnExtension.pc` |

> 客户端库 `lib/SignOn`（CMake 包 `SignOnQt6`，kaccounts-integration 的 `find_package(SignOnQt6 8.55)` 目标）
> 已作为独立包 [`libsignon-qt`](../libsignon-qt/README.md) 发布，本包不重复构建。
> 插件 SDK 的 `<SignOn/sessiondata.h>` 等客户端类型头文件来自该包（见下文"依赖关系"）。

守护进程另外安装：D-Bus 激活服务文件（`share/dbus-1/services/`）、`signond.conf` 示例配置、
服务常量头 `include/signond/signoncommon.h`、示例插件源码（`share/doc/signon-plugins-dev/example/`）。

## 鸿蒙 PC 适配要点

1. **qmake → CMake 包装**：上游只有 qmake 工程（`signon.pro` + `*.pri`），而 ohpcd 的 qtbase 包
   不提供 OHOS mkspec，qmake 无法交叉编译。本包自写 `CMakeLists.txt`（随配方分发），逐条复刻
   `signon.pro` / `signon-plugins.pro` / `SignOnExtension.pro` / `plugins.pri` 的目标、包含路径、
   `DEFINES` 与安装规则，按 Qt6 形态构建。**零上游源码补丁**（`patches/` 为空）。
2. **Qt6 SQL 来源**：守护进程 `QT += sql`（凭据库用 `QSqlDatabase`/SQLite），而 ohpcd 的
   `qtbase` 以 `FEATURE_sql=OFF` 构建（既无 `libQt6Sql.so` 也无 `lib/cmake/Qt6Sql`），
   因此 Qt6 提供方选用已发布的 **`qtbase-sql-dbus/6.11.1`**（含 `Qt6Sql` 与
   `plugins/sqldrivers/libqsqlite.so`；ktextaddons / akonadi / qmmp 同款先例）。
   其根 `cpp_info` 为 `cmake_find_mode=none`，配方 `generate()` 把 `<pkg>/lib/cmake/Qt6`
   写入 `Qt6_DIR`（libsignon-qt 8.61 同款补丁经验）。
3. **`libsignon-plugins` 不是空壳**：上游 `signon-plugins.pro` 只有 `HEADERS`，qmake 会对
   `SignOn/authpluginif.h` 跑 moc 并把生成代码编入库——`AuthPluginInterface::qt_metacast` /
   `staticMetaObject` / 虚表都在这个库里，插件通过 `LIBS += -lsignon-plugins` 解析它们。
   CMake 侧把 SDK 头文件列入 target sources 以复现同一份 moc 产物。
4. **插件命名**：qmake `CONFIG+=plugin` 产出 `lib<type>plugin.so`，插件宿主按
   `SIGNON_PLUGIN_PREFIX + type + SIGNON_PLUGIN_SUFFIX`（`lib` + `password` + `plugin.so`）查找；
   CMake 侧显式设置 `PREFIX lib`。
5. **路径不写死构建缓存**：`SIGNOND_PLUGINS_DIR` / `SIGNOND_EXTENSIONS_DIR` 编译期默认值为稳定的
   系统路径 `/usr/lib/signon`（上游默认），运行期可用 `SSO_PLUGINS_DIR` / `SSO_EXTENSIONS_DIR`
   覆盖；D-Bus `.service` 文件同样使用稳定部署前缀（`SIGNOND_DBUS_EXEC_BINDIR`，默认 `/usr/bin`）。
   `bin/signond` 的 `DT_NEEDED` / `RUNPATH` 无任何 conan 缓存路径。
6. **共享库 SONAME**：上游 qmake 从不设 `VERSION`，上游 `.so` 没有 `DT_SONAME`；本平台对 CMake 而言是
   未知系统（`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 为空），CMake 的 `VERSION`/`SOVERSION` 也不会产生
   `-soname`。适配用显式链接选项补上相对 SONAME（`libsignon-plugins.so` 等，与上游安装名一致），
   满足仓内 L5a 质量门禁（下游链接器需要 SONAME 才能按名寻址）。
7. **运行期平台缺口（D-Bus 会话总线）**：守护进程 `init()` 在装载配置、构造凭据管理器之后
   连接会话总线，失败即 `qFatal("SignonDaemon requires DBus to start working")`。
   本适配环境的缺口是**总线本身**：镜像内没有 `dbus-daemon` 可执行文件，且任何可写挂载点上
   `bind(2)` Unix socket 都返回 `EPERM`（抽象命名空间 socket 可 bind，但缺守护进程）。
   因此 `bin/signond` 实测停在上述 `qFatal`（退出码 134），守护进程↔插件的认证链路改用
   **不依赖总线的插件宿主进程**做端到端验证（见 `test_package/consumer.cpp`：真实
   `signonpluginprocess` + 真实 `libpasswordplugin.so` + 真实 blob IPC 协议）。
   接入可用会话总线后无需重编译即可运行。
8. **未适配的旁路特性**（上游默认即关闭，与本次适配无关）：`CONFIG+=enable-backup`
   （备份 D-Bus 接口）、`CONFIG+=enable-p2p`（对等总线，需 libdbus-1）、
   `CONFIG+=cryptsetup`（cryptsetup 扩展，需 libcryptsetup）、`HAVE_LIBPROXY`
   （Qt<5.5 时代的 libproxy 代理工厂，Qt6 下上游不启用）。
   `lib/signond/interfaces/*.xml` 是 git submodule（`signon-dbus-specification`），
   commit 归档中为空，故接口 XML 未安装（D-Bus 适配器代码是仓库内自带并编译进守护进程的，
   运行不受影响）。

## 依赖关系

| 依赖 | 用途 | 状态 |
|---|---|---|
| `qtbase-sql-dbus/6.11.1` | Qt6 Core / DBus / Sql / Xml / Network + SQLite 驱动插件 | 已发布 |
| `libsignon-qt/8.61`（可选） | 客户端**库** `SignOnQt6`（`SignOn::Identity`/`AuthSession` 等链接用；kaccounts-integration 消费） | 已发布 |
| — | 插件 SDK 已自洽：`include/signon-plugins/SignOn/` 内含 SDK 头所需的客户端类型头（`sessiondata.h`/`signonerror.h`/`libsignoncommon.h`/`SessionData`） | 包内提供 |

运行期无外部库依赖：凭据加密默认走内置实现（`default-secrets-storage`），SQLite 由 Qt 驱动插件提供。

## 消费方式

```bash
conan install --requires=signond/8.61-git20231015.c8ad982 -r=ohpcd -pr:h=ci/conan/profiles/ohos-aarch64
```

```cmake
find_package(Qt6 COMPONENTS Core DBus CONFIG REQUIRED)   # Qt6_DIR 指向 qtbase-sql-dbus 包内 lib/cmake/Qt6
find_package(signond CONFIG REQUIRED)
target_link_libraries(<plugin> signond::signond Qt6::Core)
```

第三方认证插件（继承 `AuthPluginInterface`，实现 `process()` 并用 `SIGNON_DECL_AUTH_PLUGIN` 导出
`auth_plugin_instance`；安装到 `<pkg>/lib/signon/lib<type>plugin.so`）只需本包：

```bash
pkg-config --cflags signon-plugins   # -I<signond>/include/signon-plugins（含 SDK 头与所需客户端类型头）
pkg-config --libs   signon-plugins   # -lsignon-plugins（AuthPluginInterface 的 moc 产物在此库中）
```

> 需要 `SignOn::Identity` / `SignOn::AuthSession` 等**客户端库**（kaccounts-integration 场景）时，另装
> `libsignon-qt/8.61` 并通过 `find_package(SignOnQt6)` 使用。

守护进程 / 插件宿主可通过环境变量调优：`SSO_PLUGINS_DIR`、`SSO_EXTENSIONS_DIR`、
`SSO_STORAGE_PATH`、`SSO_LOGGING_LEVEL`、`SSO_LOGGING_OUTPUT`（`stdout` 时日志走 stderr，
默认 `syslog`）、`SSO_CONFIG_FILE_DIR`。

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 8.61-git20231015.c8ad982 | built | 首次适配（固定 commit `c8ad982`，实际提交日期 2023-11-24；版本名中的日期为平台任务卡标识）；conan-verify PASS（G0-G4+L2/L4/L5），W3 本地 CI 通过，上游 passwordplugintest 9/9，test_package 端到端 22/22 |

## 参考资料

- 上游仓库: https://gitlab.com/accounts-sso/signond
- D-Bus 接口规范（submodule）: https://gitlab.com/accounts-sso/signon-dbus-specification
- 客户端库（本仓）: [libsignon-qt](../libsignon-qt/README.md)
- 消费方: `kaccounts-integration`（`find_package(SignOnQt6 8.55)`）、`kaccounts-providers`
