# 无桌面会话适配（一）：D-Bus 会话总线与 KDED 装载

> 适用平台：HarmonyOS PC / OHOS aarch64（无 KDE/Plasma 桌面会话）
> 关联知识：`knowledge/operations/ohos-adaptation-patterns.md`（平台差异总览）、`knowledge/doc/E461.md`（AF_UNIX file-socket bind 被拒，会话总线的常见伴生问题）
> 首例归档：`archives/k/kwrited/6.7.2`（KDE Plasma kwrited，随本主题同 PR 交付）

## 1. 问题：OHOS 上没有「桌面会话」

KF6/Plasma 生态的三方库大量假设自己跑在一个完整的桌面会话里。OHOS 侧的实际环境是：

| 桌面会话的组成 | OHOS 侧实况 | 直接后果 |
|---|---|---|
| 会话 D-Bus 总线（`DBUS_SESSION_BUS_ADDRESS` + `dbus-daemon --session`） | 不存在（无 env、无系统总线外的会话总线） | `QDBusConnection::sessionBus()` 连接失败；`KNotification` 静默无输出；`KDBusService` 起不来 |
| KDED（KDE 守护进程） | 不存在，无 `org.kde.kded` 服务 | 安装在 `plugins/kf6/kded/*.so` 的 `KDEDModule` 插件**永远不会被加载** |
| Plasma 会话/自启动管理 | 不存在 | `*.desktop` 自启动项不会被会话拉起（需应用自行 fork/wrapper） |
| 通知服务（`org.freedesktop.Notifications`） | 不存在 | 依赖通知的 UI 反馈路径需另行设计 |

这类库的典型形态是**同一个源树编出两种目标之一**：默认编成桌面会话里的插件/服务，只有某个能力探测失败时才退化成独立程序。上游把这个开关藏在 `cmake_dependent_option()` 里，与一项**外部能力**联动，检测脚本与人工审查都容易漏掉——漏掉的后果不是报警，而是**编出一个永远不被加载的产物**（CI 全绿、装机后什么都不发生）。

## 2. 检测：先跑脚本，再动配方

```sh
sh knowledge/operations/no-desktop-session-dbus-kded/detect-session-bus-deps.sh <源码目录>
sh knowledge/operations/no-desktop-session-dbus-kded/detect-session-bus-deps.sh --json <源码目录>   # 供流水线消费
```

判定语义与知识库其它检测脚本一致：**目标平台未声明支持，但源码里当真在用**。脚本把命中分成两档：

- `HARD` —— 配置期/链接期/装载期硬依赖：`find_package(KF6DBusAddons ...)`、`KF6::DBusAddons`、`COMPONENTS ... DBusAddons`、`KDEDModule` 类/`kcoreaddons_add_plugin`、`K_PLUGIN_FACTORY_WITH_JSON`、`plugins/kf6/kded` 安装目录。构建或装机必然失败/无意义 → **必须按 strategy.md 处理**，脚本 `exit 1`。
- `SOFT` —— 运行期可选依赖：`QDBusConnection::sessionBus()`、`QDBusInterface/QDBusMessage`、`KNotification`、`org.kde.kded`、`DBUS_SESSION_BUS_ADDRESS`。构建能过，但功能会退化 → 记录并确认降级路径存在，脚本 `exit 0`。

退出码：本脚本 `0` 未命中 / `1` 命中 HARD / `2` 用法错误。
注意两个检测脚本的约定**相反**，调用方须分别判定：`detect-no-desktop-session-kded-branch.sh` 为 `0` = 命中（本主题策略适用）/ `1` = MISS（不涉及会话绑定）/ `2` = 用法错误。

本机实测（`sh` + busybox awk，四个场景；`--json` 输出均以 `python3 -m json.tool` 解析通过）：

| 场景 | 输入 | 观测 | 退出码 |
|---|---|---|---|
| 命中 | kwrited 6.7.2 源码树 | `HARD=8 SOFT=3`；`--json` 的 `hits` 共 11 条，与文本模式计数一致 | `1` |
| 命中（转义边界） | 构造样例：命中行文本同时含反斜杠、双引号、CR、Tab | `hard_hits=3`；`text` 原样往返、C0 控制字符归一为空格，JSON 合法 | `1` |
| 无命中 | `archives/k/kwrited/6.7.2/test_package` | `hard_hits=0 soft_hits=0`，`"hits": []` | `0` |
| 路径边界 | `source_dir` 自身含反斜杠的目录 | `source_dir` 往返一致，JSON 合法 | `0` |

## 3. 处理策略

五种策略（A–E）与反模式清单见 [strategy.md](strategy.md)。一句话版：

> **优先让上游自带的降级开关被正确触发（零补丁），其次显式钉住无会话形态；禁止引入假的 `kdbusaddons` 包顶替，禁止用平台宏 `#ifdef __OHOS__` 绕过 `find_package` 硬依赖。**

## 4. 样例库：最小复刻两条分支

[sample/](sample/) 是一个最小 CMake 工程，去业务化复刻了 kwrited 的双分支结构（`cmake_dependent_option(BUILD_AS_EXECUTABLE ... "KPty_HAVE_UTEMPTER" ON)`）。样例自带 `conanfile.py`，依赖前缀由 `generate()` 手工写入 `conan_cmakedeps_paths.cmake`（本仓库 KF6/Qt6 配方用 `cmake_find_mode=none`，CMakeDeps 不生成该文件 —— kpty 6.26.0 / kwrited 6.7.2 先例），因此**复现全程与 CI/W3 同机制（conan 驱动）**，不手搓 cmake 命令行。

- 「关策略」= `SAMPLE_ASSUME_DESKTOP_SESSION=1`：样例把 `BUILD_AS_EXECUTABLE` 钉为 `OFF`（必须放在 `cmake_dependent_option()` 之后才能覆盖联动结果），进入会话插件分支 → `find_package(KF6DBusAddons REQUIRED)` 配置期报错；
- 「开策略」= 默认配置：KF6Pty 包导出 `KPty_HAVE_UTEMPTER=FALSE` → `cmake_dependent_option()` 强制 `BUILD_AS_EXECUTABLE=ON` → 独立可执行分支，配置 + 编译 + 运行全通。

干净环境复现（两个变体各用私有输出目录，不复用任何本地产物）：

```sh
sh knowledge/operations/no-desktop-session-dbus-kded/reproduce.sh
```

实测（conan 2.29.1 + 仓库内 `ci/conan/profiles/ohos-aarch64`，`RESULT: PASS`）：

| 步骤 | 观测 | 证据 |
|---|---|---|
| [2/4] 关策略 | 配置期报错（预期） | `By not providing "FindKF6DBusAddons.cmake" in CMAKE_MODULE_PATH ... "KF6DBusAddons", but CMake did not find one.` |
| [3/4] 开策略 | 配置 + 编译通过 | `-- session-strategy sample: KPty_HAVE_UTEMPTER=FALSE BUILD_AS_EXECUTABLE=ON` |
| [4/4] 产物 + 运行 | 独立可执行产物在无会话总线环境下运行成功 | `branch=executable pty_open=true tty=/dev/pts/1` |

## 5. 实证：kwrited 6.7.2

`archives/k/kwrited/6.7.2`（本主题的首例交付物，同 PR）：

- 上游 `CMakeLists.txt` 原文：`cmake_dependent_option(BUILD_AS_EXECUTABLE "Whether to build kwrited as executable" OFF "KPty_HAVE_UTEMPTER" ON)` —— 当 `KPty_HAVE_UTEMPTER` 为假时该选项被**强制为 ON**；
- `kpty/6.26.0` 是无 UTEMPTER 构建（包内 CMake 配置导出 `KPty_HAVE_UTEMPTER=FALSE`；该版本已于 2026-10-14 随【依赖项】PR #15405 合入 main 并发布制品仓，revision `32850cf4…`），因此 OHOS 上 kwrited 自动走**可执行分支**：产物 `bin/kwrited`，不再需要 `KF6::DBusAddons`，也不需要任何源码补丁；
- 模块分支（`plugins/kf6/kded/kwrited.so`）在 OHOS 上即使编出来也永远不会被加载，故本交付物**不引入** `kdbusaddons`；
- 消费者用例（`test_package/test_app.sh`）实跑产物并断言它持有 pty（可执行分支 `dup2(pty->slaveFd(), 0)`），把「形态选对了」从 CMake 事实变成运行时可验证事实。

## 6. 与其它已知模式的边界

- 与本平台**无关**的一类：库自带 `DBus` 依赖但只用系统总线（`QDBusConnection::systemBus()`，如 logind/upower 客户端）→ 不属于本主题，按常规「服务不存在时降级」处理；
- 运行期会话总线缺失导致的 `E461`（AF_UNIX file-socket bind 被拒）只影响**自建/自连**总线的库（如测试里 fork `dbus-daemon --session`）→ 归 `E461`，不要与本主题混记；
- 若上游只有一个纯 KDED 插件形态、无法退化成独立程序，则本主题给出的结论是**不可交付**（`env_unsupported`），而不是硬改上游去编一个不会被加载的 `.so`。
