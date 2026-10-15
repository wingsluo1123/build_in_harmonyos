# DRAFT：KF6 应用在无 D-Bus 会话总线的平台上启动即终止（KDBusService）

- **来源**：kcachegrind 26.04.0 适配（2026-10-15，KDE release-service 26.04.0）
- **严重度**：2（应用完全不可启动，但平台/配方侧有确定性修法）
- **分类**：qt6, kf6, runtime, portability

## 现象

在 OpenHarmony（无 D-Bus 会话总线）上运行构建产物：

```
$ QT_QPA_PLATFORM=offscreen DBUS_SESSION_BUS_ADDRESS=unix:path=/nonexistent \
    bin/kcachegrind --version
kf.dbusaddons: DBus session bus not found. To circumvent this problem try the
following command (with bash):
  export $(dbus-launch)
$ echo $?
1
```

任何参数（包括 `--version`）都启动即退出；二进制本身可正常加载
（`readelf -d` 的 DT_NEEDED 全部可由 DT_RPATH 解析）。

## 根因

上游 `kcachegrind/main.cpp` 在解析命令行**之前**构造 D-Bus 服务：

```cpp
KDBusService service(KDBusService::Multiple);
```

kdbusaddons（6.29.0 实测）在 `QDBusConnection::sessionBus()` 不可用时于构造函数内
终止整个进程。因此平台上只要没有会话总线，应用就没有任何可用路径。

**反面参照**：ktimer 26.04.0 的 `main.cpp` 先 `aboutData.processCommandLine(&parser)`
再构造 `KDBusService`，所以 `--version` 会在构造之前返回 0 —— **用 `--version` 冒烟
会假绿**，掩盖真实 GUI 启动路径上的同一处终止。本条目因此同时是一条**测试方法**教训：
KF6 GUI 应用不能只做 `--version` 冒烟。

## 修法（运行期能力探测，不含平台宏，符合 R8/PF5）

```cpp
#include <memory>
#include <QDBusConnection>
...
std::unique_ptr<KDBusService> service;
if (QDBusConnection::sessionBus().isConnected()) {
    service.reset(new KDBusService(KDBusService::Multiple));
}
```

- 有会话总线的系统：行为与上游完全一致（仍注册服务）。
- 无会话总线：仅跳过 D-Bus 激活；`KDBusService::Multiple` 本身无单实例语义，
  kcachegrind 不依赖它，故无功能损失。

若对象在程序内确有消费者（连接 `activateRequested` 等信号），需把消费者一并放进守卫，
或改为直接使用 `QDBusConnection`。

## 验证

```
$ conan create archives/k/kcachegrind/26.04.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
...
== 31/31 checks passed ==
KCACHEGRIND CONSUMER SMOKE: ALL PASS
```

关键断言：
- `kcachegrind --version` → rc=0，输出 `kcachegrind 26.04.0`；
- offscreen 加载 `mini.callgrind` → 进程存活 30s 未退（GUI 起来了），
  输出 `Selected  "main"` 证明 trace loader 真实完成了解析；
- 无 `Error loading shared library` / `symbol not found`。

## 适用面

- 任何在 `main()` 早期构造 `KDBusService` 的 KF6 应用（KDE Gear 大量应用）。
- 任何在容器 / CI 沙箱 / OHOS 等无会话总线环境运行的 Qt/KF6 GUI 应用。
- 泛化：启动期构造会 `qFatal`/`abort` 的可选子系统（KDBusService / KWallet /
  KGlobalAccel 类）都适用同一 `isConnected()` 守卫范式。

## 边界

- 不要把它当成「构建期应关掉 DBus」的理由（那是 `USE_DBUS=OFF` 选型问题）。
- 若应用**依赖** D-Bus 单实例语义才能正确工作，跳过构造会导致多实例并行——此时需在
  产品层显式接受该降级并在 PR 说明。
