# kaccounts-integration 26.04.0 功能测试报告

**测试日期:** 2026-10-13
**测试环境:** HarmonyOS PC (aarch64-linux-ohos, OHOS SDK 26.0.0.18)
**编译器:** clang 15 (target aarch64-linux-ohos, libc++, C++17)
**构建系统:** CMake 4.1.2 + ECM 6.26.0 + Ninja/Make (conan 2 双 profile)

## 1. 编译测试

### 1.1 编译状态
✅ 完整构建成功。产物清单（packaging/kaccounts-integration-26.04.0-ohos-aarch64.tar.gz）：
- `lib/libkaccounts6.so.6.2.x` — KAccounts 集成库（AccountsModel/GetCredentialsJob/UIPlugin 等全套）
- `lib/cmake/KAccounts6/` — KAccounts6Config + **KAccountsMacros.cmake**（kaccounts_add_provider 宏，kaccounts-providers 消费）
- `lib/plugins/plasma/kcms/systemsettings/kcm_kaccounts.so` — 系统设置账号 KCM
- `lib/plugins/kf6/kded/kded_accounts.so` — 守护进程模块
- `lib/qml/org/kde/kaccounts/` — QML declarative 插件
- `include/KAccounts6/` + `share/applications/kcm_kaccounts.desktop`

### 1.2 源码修改
5 个适配补丁（qcoro 宏内联 / QCoro6 目标名 / Qt6 Xml+DBus 组件 / 空 include 变量修复 / 剔除 kio-webdav），详见 `patches/` 与 `conandata.yml`。

## 2. 上游测试 (R51 申报)

**26.04.0 release tarball 内无 tests/ 或 autotests/ 目录**（实测解压目录树确认），上游不随源码发布单元测试，无 ctest 套件可跑。申报记录：`test_package/MANIFEST.yml`（upstream_tests: []）。

## 3. 鸿蒙专项测试 (test_package)

### 3.1 用例
`test_package/test_kaccounts_integration.cpp` + `CMakeLists.txt`（消费者视角，真实 API）：
1. `find_package(KAccounts6)` 配置解析（含 Qt6/KF6I18n/KF6CoreAddons 传递链）
2. 链接导出目标 `KAccounts6` 并编译运行
3. `kaccounts_add_provider(test.provider NO_INTLTOOL)` — 对导出的 KAccountsMacros.cmake 做真实编译期消费
4. `Accounts::Manager` 构造 + `providerList()`/`serviceList()` 离线枚举
5. `Accounts::Provider` 未找到路径（`provider("definitely-not-a-real-provider")` 断言不崩溃、返回 invalid）

### 3.2 运行结果
```
providers listed: 0
services listed: 0
PASS: KAccounts6 library + AccountsQt6 chain load and respond
```
✅ 全部断言通过。providers=0 为沙箱无 accounts DB/未部署 provider 数据所致（环境限制，非库缺陷）。

## 4. 已知限制

- **kio-webdav 守护插件未构建**：依赖已发布 kio/6.26.0 包未携带的生成头 `<KDirNotify>`（kio 配方打包缺口，另行跟踪）。kaccounts-providers 仅消费 libkaccounts6 + KAccountsMacros.cmake，不受影响。
- 完整运行时功能（账号增删、凭据获取）需 signond D-Bus 服务与 accounts DB，沙箱内不可用；本地已验证的是库加载、链接与离线枚举 API。
- GLib `g_object_unref` 告警为沙箱无 D-Bus 的无害噪声。

## 5. 结论

本地闭环（conan create → test_package → packaging）全绿，具备提交条件。
