# kaccounts-integration 26.04.0 — 鸿蒙PC (aarch64-linux-ohos) 适配笔记

- 日期: 2026-10-13
- 分支: feat/kaccounts-integration-26.04.0
- 状态: 本地闭环通过（conan create + test_package 全绿）

## 概要

KAccounts 集成库（libkaccounts6 + KCM + kded 守护插件 + QML 插件），KDE Release
Service 26.04.0。CMake + ECM + KF6，Qt6 ≥ 6.5。是 kaccounts-providers 26.04.0
的硬构建依赖（kaccounts_add_provider 宏与 KAccounts6 目标）。

## 上游测试清点 (R51)

26.04.0 release tarball 内无 tests/ 或 autotests/ 目录（实测解压目录树确认），
上游不随源码发布单元测试。test_package 提供消费者冒烟测试
（find_package(KAccounts6) + 链接 KAccounts6 + kaccounts_add_provider 宏 +
Accounts::Manager 离线 API），见 test_package/MANIFEST.yml。

## OHOS 适配要点（补丁 0001–0005）

1. **qcoro 宏缺失** (0001)：上游顶层 CMakeLists 调用 `qcoro_enable_coroutines()`；
   该宏在包内 `lib/cmake/QCoro6Coro/QCoroMacros.cmake`，CMakeDeps 生成的
   QCoro6Config 不带它。补丁在 `COMMAND qcoro_enable_coroutines` 不存在时内联
   定义（Clang<16: `-fcoroutines-ts`；Clang≥16 / C++20 默认开启）。
2. **QCoro6::Core 目标名** (0002)：kio-webdav 硬编码 Qt5 别名 `QCoro::Core`，
   改 `QCoro6::Core`。
3. **Qt6 组件需求** (0003)：src/lib 链接 `Qt::Xml`，kio-webdav 经 SignOnQt6 静态
   库需要 Qt6DBus 符号（QDBusError 等），顶层 find_package 增加 `Xml DBus`。
4. **空 include 变量** (0004)：上游 src/lib 的
   `target_include_directories(kaccounts SYSTEM PUBLIC "${ACCOUNTSQT_INCLUDE_DIRS}")`
   —— ACCOUNTSQT_INCLUDE_DIRS/SIGNONQT_INCLUDE_DIRS 是 pkg-config 时代变量，
   CMakeDeps 下恒为空，空参数被相对化为 `<srcdir>/src/lib/` 并以
   "INTERFACE_INCLUDE_DIRECTORIES prefixed in the source directory" 报错。
   同时 `${ACCOUNTSQT_LIBRARIES}`/`${SIGNONQT_LIBRARIES}` 变量式链接在 CMakeDeps
   下为空，导致 Accounts/SignOn 头文件与 Qt6DBus 符号缺失。补丁改为链接
   `AccountsQt6::AccountsQt6` / `SignOnQt6::SignOnQt6` imported target（include
   经 target 传递）。
5. **kio-webdav 剔除** (0005)：该插件 include `<KDirNotify>`（qdbusxml2cpp 生成
   头），发布的 kio/6.26.0 包未携带（kio 打包缺口，另行跟踪；PF1 禁止捎带修改
   kio）。OHOS 版剔除 `add_subdirectory(kio-webdav)`，其余组件（lib/declarative/
   plugins/kcm/kded）完整构建。

## 配方要点

- 依赖收敛（override）：qtbase→6.11.1.1（qtdeclarative pin 6.11.1 冲突）、KF6
  各包→6.26.0（kwallet/kio 6.18 line 的 pin 收敛）、zlib→1.3.2（glib2 pin
  1.3.1 冲突）。
- qtbase 映射：`cmake_file_name=Qt6` + `cmake_target_name=Qt6::Core`（吃掉
  qcoro 等包记录的 `qtbase::qtbase` 全局目标引用），`Qt6_DIR` 指向
  `<qtbase>/lib/cmake/Qt6`。
- KF_SKIP_PO_PROCESSING=ON；KF_IGNORE_PLATFORM_CHECK=TRUE；BUILD_TESTING=OFF。
- conandata.yml 扁平 sources 结构（E017 要求），patches 版本键控。

## 已知缺口 / 申报

- **kio-webdav 插件缺失**：依赖 kio 包未发布的生成头 kdirnotify.h。kaccounts
  kded 守护、KCM、QML 插件、libkaccounts6 全部可用；仅 DAV 目录通知插件缺失。
  后续 kio 配方补齐 kdirnotify.h 后可去掉补丁 0005 重新出包。
- **运行时依赖**：完整功能需 signond（8.61）D-Bus 服务与 accounts DB；沙箱内无
  D-Bus/accounts 服务，test_package 以离线 API（providerList/serviceList/
  provider 未找到路径）验证。
- ohpcd 上 libaccounts-qt/1.17 二进制缺 cpp_info metadata，消费者 CMakeDeps
  include 目录为空；test_package 用 data 变量显式补路径（kaccounts-providers
  适配时同样注意）。

## 实测结果

- conan create（ohos-aarch64 profile）：configure/build/install 通过，
  产物含 libkaccounts6.so、kcm_kaccounts.so（kcms/systemsettings）、
  kded_accounts.so、kaccountsdeclarativeplugin（qml）。
- test_package：PASS（"KAccounts6 library + AccountsQt6 chain load and
  respond"；GLib g_object_unref 告警为沙箱无 D-Bus 的无害噪声）。
---

**编译结束**: 2026-10-13 21:01
**最终状态**: built
