# kwrited

## 是什么

KDE Plasma 的 **kwrited** 守护进程：作为 `write(1)` 的接收端，把发往终端的消息**以桌面通知呈现**
（上游自述 “kwrited is a write(1) receiver for KDE”，实现依赖 `KNotification` + `kwrited.notifyrc`）。
上游仓库 <https://invent.kde.org/plasma/kwrited>，本归档适配 Plasma 6.7.2 同版源码（`stable/plasma/6.7.2`）。

它本身是 KDE 桌面会话的部件，但在 OHOS 上恰好有一条**上游自带**的无会话路径 —— 本归档交付的就是这条路径。

## 关键机制：形态由 KF6Pty 的能力宏决定（零补丁）

上游 `CMakeLists.txt` 原文：

```cmake
cmake_dependent_option(BUILD_AS_EXECUTABLE "Whether to build kwrited as executable" OFF
    "KPty_HAVE_UTEMPTER" ON)
```

| 分支 | 触发条件 | 目标产物 | 额外依赖 | OHOS 可行性 |
|---|---|---|---|---|
| 会话插件（上游默认） | `KPty_HAVE_UTEMPTER` 为真 | `lib/plugins/kf6/kded/kwrited.so`（`KDEDModule`） | `KF6::DBusAddons` + KDED 装载 | ❌ 无会话 D-Bus 总线、无 KDED → 永不加载 |
| 独立可执行程序 | `KPty_HAVE_UTEMPTER` 为假 | `bin/kwrited` | 无（不 `find_package` DBusAddons） | ✅ 本归档交付路径 |

OHOS 侧的 `kpty/6.26.0` 是无 UTEMPTER 构建（包内 CMake 配置导出 `KPty_HAVE_UTEMPTER=FALSE`，
本交付的前置依赖，源码与配方见主仓 `archives/k/kpty/6.26.0`，
已于 2026-10-14 随【依赖项】PR #15405 合入 main 并发布制品仓，revision `32850cf489da395267d4cfe789ffce7e`），
因此 **kwrited 在 OHOS 上自动落到可执行分支**：
不需要源码补丁、不需要 `kdbusaddons`、不需要伪造任何能力探测。

> 这条路径不是"绕过依赖"，而是上游为无 UTEMPTER 平台（容器/嵌入式）准备的既有形态；
> 判定与验证口径见知识库主题 [`knowledge/operations/no-desktop-session-dbus-kded`](../../../knowledge/operations/no-desktop-session-dbus-kded/README.md)。

## 依赖（与已合入 main 的 KF6 6.26 配方逐字对齐）

| 依赖 | 针脚 | 用途 | 制品仓 |
|---|---|---|---|
| qtbase | `6.11.1` | `Qt6::Core/Gui`（上游要求 `QT_MIN_VERSION 6.10.0`） | ✅ |
| kcoreaddons | `6.26.0.1` | `KAboutData`/`KPluginFactory` | ✅ |
| ki18n | `6.26.0` | 翻译（`ecm_qt_translation_install`） | ✅ |
| knotifications | `6.26.0` | `KNotification`（无会话总线时运行期静默降级） | ✅ |
| kpty | `6.26.0` | `KF6::Pty`：可执行分支的判定源 + pty 本体 | ✅ 已有（2026-10-14 随 PR #15405 合入并发布，R36 前置已解除） |
| ecm (tool) | `6.26.0` | `ECM`/`KDEInstallDirs6`/`KF6` 查找模块 | ✅ |

传递依赖：`kconfig/6.26.0`、`gettext/0.22.5`。**不需要 `kdbusaddons`**（仅插件分支才 `find_package`）。

## 测试

- 上游 **无任何测试目标**（源码包 15 个条目，无 `autotests/`、无 `add_test()`/`ecm_add_test()`），清点证据见 [`6.7.2/test_package/MANIFEST.yml`](6.7.2/test_package/MANIFEST.yml)；
- 按 R51 / 积分赛口径补**鸿蒙独有消费者用例** [`6.7.2/test_package/test_app.sh`](6.7.2/test_package/test_app.sh)：offscreen QPA 实跑 `bin/kwrited` → 存活断言 → `/proc/<pid>/fd/0` 必须是 `/dev/pts/N`（证明可执行分支确实把 pty 接管到 stdin）→ SIGTERM 优雅退出。

## 版本索引

| 版本 | 状态 | 说明 |
|---|---|---|
| 6.7.2 | built | 首个适配版本：上游双分支机制自动落到可执行分支，零补丁；消费者用例实跑通过 |
