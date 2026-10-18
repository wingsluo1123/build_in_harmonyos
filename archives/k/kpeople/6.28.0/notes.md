# kpeople 6.28.0 — HarmonyOS PC 适配笔记

## 基本信息

- 包名 / 版本：`kpeople` 6.28.0（KDE Frameworks 6.28.0）
- 源码：`https://download.kde.org/stable/frameworks/6.28/kpeople-6.28.0.tar.xz`（sha256 `a5bcf11a…fd0a`）
- 适配日期：2026-10-16；真机验证通过（conan-verify PASS）
- 依赖 / 工具链：
  - 运行依赖：`qtbase-sql-dbus/6.11.1`（vanilla qtbase 没有 FEATURE_sql）、`qtdeclarative/6.11.1`、`kcoreaddons`/`kwidgetsaddons`/`ki18n`/`kitemviews`/`kcontacts` 6.18.0
  - 构建依赖：`ecm/6.26.0`
  - 编译器：clang 15.0.4；hnp cmake 4.1.2；Unix Makefiles；原生编译（host=build）

## 上游结构（4 个产物 + 3 套测试）

| 目标 | 位置 | 说明 |
| --- | --- | --- |
| `KF6People` | src/ | 核心库：PersonsModel / PersonData / PersonManager / 合并求解 |
| `KF6PeopleBackend` | src/backends/ | 数据源插件接口 + vcard 后端 |
| `KF6PeopleWidgets` | src/widgets/ | 视图组件 |
| `KF6PeopleDeclarative` | src/declarative/ | QML 模块（`ecm_add_qml_module`，URI `org.kde.people`） |

autotests/ 三个测试目录：`persondatatest`、`personsmodeltest`、`personsproxymodeltest`。

## 坑与解法

### 坑 1（本包最大）：`UNIX` 为真让 USE_DBUS 被自动打开 → 合并通知在总线回环处静默丢失

- 配方按平台真名口径设 `CMAKE_SYSTEM_NAME=OHOS`，SDK 自带的 `Platform/OHOS.cmake` 全文是
  `include(Platform/Linux)` → `UNIX` 为真。
- kpeople 上游 `CMakeLists.txt:33-43` 自己推导默认值：`USE_DBUS_DEFAULT OFF`，
  `if(UNIX AND NOT APPLE AND NOT ANDROID AND NOT HAIKU)` 时置 ON（注释原话
  "enabled per default on Linux & BSD systems"）→ `USE_DBUS=ON` → `find_package(Qt6 DBus)`
  成功（qtbase-sql-dbus 变体携带 DBus）→ `HAVE_QTDBUS=1` 进入编译定义。
- `src/personmanager.cpp` 里通知路径被整体换血：构造函数在 `#if HAVE_QTDBUS` 下把总线信号
  回环到本地槽（67-80 行）；`mergeContacts()` 成功后的广播，`#if HAVE_QTDBUS` 分支用
  `QDBusConnection::sessionBus().send(...)`，`#else` 分支才直接发本地信号（219-239 行）。
- 设备上没有会话总线：`send()` 静默失败（返回值被忽略）、回环永不触发 → 本地信号从头到尾
  没有被发过。而 `PersonsModel` 监听的就是这两个**本地**信号（`src/personsmodel.cpp:95-96`），
  它不做任何总线订阅 → 数据库事务已提交（`mergeContacts` 返回了合法的 `kpeople://1`），
  内存模型却维持旧行数。
- 测试碰撞：`personsmodeltest` 在合并后 `QTRY_COMPARE(model->rowCount(), 3)`（第 77 行）
  失败（保持 4）；随后的 `gettersTests` 对空 `indexList` 取 `first()` 触发 QFATAL →
  OHOS 崩溃处理循环（同一信号反复重放、进程不退出、TERM 不响应），把 ctest/relay 一起挂死。
- 排查链（可复用）：`CMakeCache.txt` 看 `USE_DBUS:BOOL=ON` → 编译单元 `flags.make` 看
  `-DHAVE_QTDBUS=1` → 源码读 `#if HAVE_QTDBUS` 分支 → 把 `QTRY_TIMEOUT` 提到 60000
  对照排除时序（无效，说明不是慢而是通知永远不会到）。
- 修复：配方在 OHOS 分支显式 `tc.variables["USE_DBUS"] = "OFF"`，选上游为所有非 Linux 系统
  保留的进程内信号路径。修复后 `personsmodeltest` 6.14s 通过。
- 口径参照：KF5 姊妹包 kpeople5/5.116.0 天然没有 `QT_DBUS_LIB`，走的正是进程内路径
  （其 notes 原文："PersonManager 的 dbus 通知在 QT_DBUS_LIB 未定义时编译掉"）。
  KF6 只是把「非 Linux ⇒ 进程内」作为默认，我们把 OHOS 显式归回这一类。

### 坑 2：Conan 2.29 的 `cache_variables` 只写进 CMakePresets.json，不进 conan_toolchain.cmake

- 本配方用 `-DCMAKE_TOOLCHAIN_FILE=…/conan_toolchain.cmake` 手工配置（不走 `--preset`），
  而 Conan 2.29 把 `CMakeToolchain.cache_variables` 只写进 `generators/CMakePresets.json`
  的 `cacheVariables` 段 → 手工配置路径静默看不到。
- 症状：`CMAKE_PLATFORM_NO_VERSIONED_SONAME` 没生效 → 链接后 CMake 建版本化符号链接被
  HMDFS 拒（EPERM）→ 构建失败。连试数轮、比对 CMakeCache 才定位。
- 解法：凡是「必须到达 CMake」的变量一律走 `toolchain.variables`（会被写进
  `conan_toolchain.cmake`），已固化在 `_configure_ohos_shared_library_rules` 的注释里。
- 查重备注：与 E622（libheif）的 forbid_5/子工程陷阱是同一底层机制（那边是子工程只拿
  toolchain 文件），本条属主工程手工配置场景，不另立知识条目，记录在本笔记。

### 坑 3：HMDFS 无符号链接 → 库命名与测试运行期布置

- `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` + 自写的 `ohos-shared-library-rules.cmake`
  （经 `CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX` 注入 `-Wl,-soname,` / `-Wl,-rpath,`）：
  链接期只产出 `libKF6People.so` 单文件，但 `DT_SONAME` 真实在位，消费者记录的
  `DT_NEEDED` 是可重定位的名字（对照 DRAFT-cmake-harmonyos-system-name-soname）。
- `_prepare_ctest_runtime_links()` 把依赖库布置到 `build/bin` 与 `build/../bin`
  （symlink 失败自动退化为拷贝），配合 `$ORIGIN` 构建 RPATH 让测试二进制就近解析依赖。

### 坑 4：KF6 版本墙（补丁 0001-CMakeLists.txt.patch）

- 上游钉 `KF_DEP_VERSION=6.28.0` 且 `find_package(ECM 6.28.0)`；ohpcd 基线是
  KF6 6.18.0 / ECM 6.26.0（kcontacts 链）。
- 补丁三处：`KF_DEP_VERSION` → 6.18.0、ECM 探测 → 6.26.0、删 `ki18n_install(po)`
  （无 Qt Linguist 工具；kcontacts 先例）。影响面仅限构建期版本门槛与语言目录安装，
  不改运行时代码。

### 坑 5：ctest 需要 `--timeout`（OHOS 崩溃处理循环）

- OHOS 上 QFATAL/abort 之后崩溃处理器会反复重放信号、进程不退出；没有超时的 ctest
  会永久等待。上游测试统一走 `ctest --output-on-failure --no-tests=error --timeout 300`，
  把「挂死」转换成「失败」。

## CMake 开关表

| 开关 | 值 | 原因 |
| --- | --- | --- |
| `BUILD_SHARED_LIBS` | ON | 交付共享库 |
| `BUILD_TESTING` | ON | 跑上游 3 套测试 |
| `BUILD_QCH` / `ENABLE_EXAMPLES` | OFF | 无文档/示例工具，缩短构建 |
| `KF_IGNORE_PLATFORM_CHECK` | TRUE | 非 Linux 平台放行 |
| `KF_SKIP_PO_PROCESSING` | ON | 无 Qt Linguist |
| `USE_DBUS` | **OFF** | 坑 1：无会话总线，选进程内信号路径 |
| `CMAKE_SYSTEM_NAME` | OHOS | 平台真名，Platform/OHOS.cmake 由 SDK 携带 |
| `CMAKE_PLATFORM_NO_VERSIONED_SONAME` | ON | 坑 3：HMDFS 拒符号链接 |
| `CMAKE_INSTALL_LIBDIR` | lib | 统一安装布局 |
| `CMAKE_BUILD_RPATH` + `--disable-new-dtags` | `$ORIGIN` | 运行期相对解析 |

## 上游测试（R51 口径）

- 三个 ctest 目标、共 10 个用例函数（不计 initTestCase/cleanupTestCase）：
  - `persondatatest`（5）：loadContact / loadPerson / contactChanged / nullPerson / removeContact
  - `personsmodeltest`（4）：loadModel / mergeContacts / gettersTests / unmergeContacts
  - `personsproxymodeltest`（1）：testFiltering
- 真机全量 10/10 通过（2026-10-16）：persondatatest 0.29s、personsmodeltest 6.14s、
  personsproxymodeltest 0.13s。
- 备注：修坑 1 之前 `personsmodeltest` 确定性失败（rowCount 4 vs 3 + 崩溃循环），
  修复后三目标全绿——这条失败本身就是坑 1 的判据。

## 验证结果（真机 conan-verify，2026-10-16）

- 上游 ctest：3/3 目标、10/10 用例。
- test_package：ctest 2/2（`test_kpeople` 6 用例 + `test_kpeople_ohos` 4 用例，合计 10/10；
  两个可执行文件也各自直接跑过）。
- 报告：`reports/conan-create.log`、`reports/conan-verify-report.md`（Verdict: PASS，
  含 G1 `export_sources()` 方法、G2 双端 profile、G4 说明项）。

## 注意事项

- 若未来产品侧确实需要**跨进程**联系人变更广播，才需要一条会话总线（参照
  DRAFT-dbus-1.14.10.1-ohos-session-bus-runtime）；库内默认走进程内信号是本适配的选型，
  KF5 姊妹包同口径。
- 消费者接线沿用 `cmake_find_mode=none` + `conan_cmakedeps_paths.cmake` 模式
  （kunifiedpush / kcrash 同款），vanilla qtbase 必须留在 CMake 搜索路径之外，
  避免与 sql-dbus 变体混树。

- 构建日志 `reports/conan-create.log` 依平台规则不随档（reports/ 仅随档脱敏 md）；脱敏的 `reports/conan-verify-report.md` 保留随档。
