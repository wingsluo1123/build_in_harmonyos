# signond 8.61-git20231015.c8ad982 测试报告

> **项目**: signond（accounts-sso Single Sign On daemon）
> **测试日期**: 2026-10-16
> **测试环境**: HarmonyOS HongMeng Kernel 1.12.0 aarch64（OHOS SDK 26.0.0.18 / clang 15）
> **测试类型**: 上游官方测试套件（可运行子集）+ test_package 端到端消费者用例

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试套件（可运行 1/4，见 §3.1） | 9 | 100% |
| test_package 用例（CASE 1/2/3/E） | 4 | 100% |
| test_package 断言（consumer.cpp 22 + Python 侧 16） | 38 | 100% |
| W3 本地 CI 门禁（L1a/L1b/L1c/L1e/L4/L5） | 6 | 100%（L2 skip：守护进程无 --version/--help） |
| 失败 (FAIL) | 0 | 0% |

**核心功能通过率**: ✅ **100%（可运行范围内）**

---

## 二、测试结论

### 2.1 总体评价

✅ **适配完成**：守护进程、插件宿主进程、两个认证插件、插件/扩展 SDK 全部按 qmake 语义构建并安装；
上游 `tests/passwordplugintest` 9/9 通过；守护进程↔插件认证链路（真实 `signonpluginprocess` +
真实 `libpasswordplugin.so` + 真实 blob IPC 协议）两条流程端到端通过；插件 SDK 头自洽性经
`QLibrary` + `auth_plugin_instance` 进程内加载验证；产物契约、SONAME 与 ELF 路径检查全部通过。
**范围说明**：D-Bus 服务注册与 `AuthService`/`Identity`/`AuthSession` 接口在本环境（无会话总线）
无法验证，CASE 1 只覆盖到「全量初始化后停在总线探测」这一步。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 平台无 D-Bus 会话总线（无 `dbus-daemon`；可写挂载点 `bind(2)` Unix socket 返回 EPERM） | 守护进程无法完成 D-Bus 服务注册，实测停在 `qFatal("SignonDaemon requires DBus to start working")`（退出码 134） | 🔴 环境缺口（非配方缺陷） |
| `tests/signond-tests`、`tests/libsignon-qt-tests`、`tests/extensions` 需要运行中的守护进程 + 会话总线 | 上游集成套件无法在本环境实跑 | 🟡 同上，未修改上游测试源码 |
| 上游 `.so` 无 `DT_SONAME`，本平台 CMake 也不产生 `-soname` | 首轮 W3 本地 CI 的 L5a 门禁报 3 个库缺 SONAME | 🟢 已修复（显式 `LINKER:-soname`），修复后 L5a 0 error、L5 通过；test_package 增加 SONAME 断言防回归 |

### 2.3 可用功能清单

```
✅ 守护进程二进制：配置装载、环境变量覆盖（SSO_*）实测可达；`CredentialsAccessManager` 对象构造按代码顺序执行（其 ctor 只建 `KeyHandler`），而凭据库 `CredentialsDB`（Qt SQL/SQLite）由 `openCredentialsSystem()` 在总线探测**之后**打开，本环境未验证
✅ 插件宿主：按 SSO_PLUGINS_DIR 定位 lib<type>plugin.so、QLibrary 加载、AuthPluginInterface 转换
✅ password 插件：密钥直返 / 无密钥→UI 回问→补答→结果，两条流程端到端通过
✅ 插件 SDK：libsignon-plugins（AuthPluginInterface moc 产物）、libsignon-plugins-common（blob IPC）
✅ 扩展 SDK：libsignon-extension
✅ 安装产物：bin/lib/include/pkgconfig/dbus service/conf 全量就位；三个 SDK 库带相对 DT_SONAME
✅ 插件 SDK 自洽：仅凭本包即可编译并加载第三方认证插件（CASE E 实证）
⚠️ D-Bus 服务注册：需宿主环境提供会话总线（配方与二进制已就绪，接入总线后无需重编译）
❌ 备份接口 / p2p 总线 / cryptsetup 扩展：上游默认关闭，本次未启用（与适配无关）
```

### 2.4 已知限制

1. 本环境无 D-Bus 会话总线，守护进程只能验证到总线探测阶段；插件链路的等价验证见 §3.2 CASE 2。
2. 插件**库**（`SignOnQt6`，`SignOn::Identity`/`AuthSession` 等链接用）仍在独立包 `libsignon-qt`；
   插件 **SDK**（编译插件所需头 + `libsignon-plugins`）已自洽，无需额外包。
3. `lib/signond/interfaces/*.xml` 是 git submodule，commit 归档中为空，故未安装（不影响运行）。

---

## 三、测试详情

### 3.1 上游测试（配方 `build()` 内实跑）

上游测试工程 `tests/tests.pro` 共 4 个 SUBDIRS，逐套清点与实际执行情况：

| 套件 | 测试程序数 | 是否实跑 | 说明 |
|------|-----------|----------|------|
| `tests/passwordplugintest` | 1（7 个测试函数 + init/cleanupTestCase） | ✅ 实跑 | 直接实例化真实 `PasswordPlugin`，驱动 `process()` / `userActionFinished()` / `refresh()`，校验 `result` / `error` / `userActionRequired` 信号载荷；**不需要**运行中的守护进程 |
| `tests/libsignon-qt-tests` | 1（42 项） | ❌ 未跑 | 经 `tests/run-with-signond.sh` + `tests/testsession.conf` 驱动运行中的 signond 与会话总线；平台无总线。且其测试对象 `lib/SignOn` 属独立包 `libsignon-qt` |
| `tests/signond-tests` | 5（+2 需 libqtdbusmock） | ❌ 未跑 | 全部由 `run-with-signond.sh` 在会话总线上运行；平台无总线 |
| `tests/extensions` | 1 | ❌ 未跑 | 依赖运行中守护进程；且被测的 `src/extensions/cryptsetup` 上游默认关闭（需 libcryptsetup） |

实跑命令与结果：

```bash
$ ctest --output-on-failure          # 目标 signon-passwordplugin-tests
    Start 1: signon-passwordplugin-tests
1/1 Test #1: signon-passwordplugin-tests ...... Passed
100% tests passed, 0 tests failed out of 1

Totals: 9 passed, 0 failed, 0 skipped, 0 blacklisted, 2ms
********* Finished testing of PasswordPluginTest *********
```

### 3.2 test_package 端到端消费者用例

| 用例 | 构造输入 | 真实执行 | 产出结果 | 校验内容 |
|------|----------|----------|----------|----------|
| CASE 1 守护进程启动（鸿蒙主机实跑） | `SSO_LOGGING_OUTPUT=stdout`、`SSO_STORAGE_PATH=<tmp>` | 执行已安装的 `bin/signond` | stderr 启动轨迹 + 退出码 | 断言出现 `SignonDaemon requires DBus to start working`、`EXIT=134`（SIGABRT），证明守护进程完成配置装载等**总线之前**的初始化步骤后停在平台唯一的 D-Bus 缺口（凭据库打开在其后，未验证） |
| CASE 2 认证端到端（不经 D-Bus） | `{UserName:"alice", Secret:"s3cr3t"}`；`{UserName:"bob"}` | spawn 已安装 `bin/signonpluginprocess password`（`SSO_PLUGINS_DIR=<pkg>/lib/signon`）→ 用 `libsignon-plugins-common` 的 `BlobIOHandler` 按 `ipc.h` 协议发起 `PLUGIN_OP_PROCESS` / `PLUGIN_OP_PROCESS_UI` / `PLUGIN_OP_STOP` | `PLUGIN_RESPONSE_RESULT` / `PLUGIN_RESPONSE_UI` 帧 + 插件宿主正常退出 | 15 项断言：插件宿主启动与插件加载、两条流程的信号/载荷逐字段比对（UserName/Secret/QueryPassword）、UI 回问后补答的密钥进入结果、退出码 0 |
| CASE 3 产物契约 | 声明的 19 个产物路径 + 3 个 SDK 库 | 文件系统检查 + `readelf -d`（`libsignond` 与 3 个 SDK 库） | 缺失列表 / `.dynamic` 内容 | 断言无缺失产物；3 个 SDK 库均带相对 `DT_SONAME`（L5a 门禁口径）；`DT_NEEDED` 含 `libQt6Sql.so.6`/`libQt6DBus.so.6`/`libsignon-extension.so`/`libsignon-plugins-common.so`；`DT_NEEDED`/`RPATH`/`RUNPATH` 中无 `/storage/`、`.conan2` 私有缓存路径 |
| CASE E 插件 SDK 自洽（进程内） | `<pkg>/lib/signon/libpasswordplugin.so` 路径 + SDK 头 | `QLibrary` 加载插件 → `resolve("auth_plugin_instance")` → 构造 `AuthPluginInterface`；构造 `SignOn::SessionData`/`SignOn::Error` | 插件实例与工厂指针、`type()`/`mechanisms()` 字符串、客户端类型属性值 | 7 项断言：插件可加载、工厂可解析、实例可创建、类型/机制正确、`SessionData` 往返、`Error` 类型正确 —— 证明 SDK 头（含 `<SignOn/sessiondata.h>` 等客户端类型）可独立编译使用且 moc 符号齐全 |

CASE 2 实测输出（节选）：

```
PASS CASE A: plugin host process started
PASS CASE A: password plugin loaded from the packaged plugin directory
     response: Secret=s3cr3t UserName=alice
PASS CASE B: UserName round-tripped through the IPC blob
PASS CASE B: Secret round-tripped through the IPC blob
     request:  QueryPassword=true UserName=bob
PASS CASE C: the UI request asks for the password
     response: Secret=pw2 UserName=bob
PASS CASE C: the user-supplied secret reached the result
PASS CASE D: plugin host exited cleanly after PLUGIN_OP_STOP
PASS CASE E: packaged SDK header + QLibrary load the packaged plugin
PASS CASE E: auth_plugin_instance factory resolved through the SDK
PASS CASE E: qobject_cast-able AuthPluginInterface instance created
PASS CASE E: plugin reports the password type
PASS CASE E: plugin advertises the password mechanism
PASS CASE E: SignOn::SessionData from the packaged SDK round trips
PASS CASE E: SignOn::Error from the packaged SDK compiles and reports its type
TOTAL pass=22 fail=0
```

### 3.3 配方验证（8 门禁）

```bash
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify signond 8.61-git20231015.c8ad982
Verdict: PASS
```

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 预构建风险评估 | ✅ | 知识图谱预查询 |
| G1 配方完整性 | ✅ | conanfile.py / conandata.yml / test_package（含 MANIFEST.yml）齐备 |
| G2 conan create | ✅ | 干净源码构建 + 上游测试 + test_package 三组用例 |
| G3 系统同名库隔离 | ✅ | 产物为 `libsignon-*`，与 `/lib` 无同名冲突 |
| G4 产物完整性 | ✅ | bin/lib/include/pkgconfig/dbus service 全量 |
| W3 本地 CI（finish 内） | ✅ | setup.sh + build_and_test.sh 通过：L1a/L1b/L1c 实跑证据、L1e 破坏性反向验证、L4/L5 pass、L2 skip |
| L2 | ⚠️ skip | smoke（`--version`/`--help`）：`signond`/`signonpluginprocess` 是守护进程/插件宿主，无这两个选项（非阻塞）；功能面改由 test_package CASE 1/2/E 覆盖 |
| L4 | ✅ | 静态安全扫描（无补丁） |
| L5 | ✅ | 产物基线 + **SONAME 门禁**：修复前 L5a 报 3 个库缺 `DT_SONAME`，补 `LINKER:-soname` 后 0 error（test_package 亦断言 SONAME） |
