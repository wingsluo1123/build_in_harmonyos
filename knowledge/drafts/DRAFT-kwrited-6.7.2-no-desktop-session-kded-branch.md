# kwrited 6.7.2：无桌面会话下 KDED 插件形态不可加载，走上游能力宏驱动的可执行形态

- **归属**：`kwrited/6.7.2`（Plasma 6.7.2）｜分类：platform compat｜严重度：medium
- **主题目录**：`knowledge/operations/no-desktop-session-dbus-kded/`
- **状态**：草稿（本机实测：手动 `conan create` 全绿、`conan-verify` G0–G4 PASS（G4 附 ⚠️：校验工具未定位 cache 包目录，产物清单以本机实测为准）、干净环境双验证 PASS；
  证据均在 PR 内可读 —— `archives/k/kwrited/6.7.2/notes.md` §4 验证结果、
  `archives/k/kwrited/6.7.2/manifest.yaml` 的 `test_results.gates`、`archives/k/kwrited/6.7.2/test_package/MANIFEST.yml`。
  注：W3 本地 CI 模拟已于 2026-10-15（前置依赖 `kpty/6.26.0` 发布后）重跑全绿：`L0_RESULT=pass`、`L1_RESULT=pass`、
  `.ci-result.json` 已写入（`exit_code=0`），详见 notes.md §4；
  `archives/k/kwrited/6.7.2/reports/` 被 .gitignore 忽略、不随 PR 出现）

## 现象

KDE/Plasma 系组件中有一类**默认形态是 KDED 会话插件**：产物装到
`plugins/kf6/kded/*.so`，随附 KPlugin 元数据（`ServiceTypes=["KDEDModule"]`、
`X-KDE-Library`），由 **KDED**（KDE Daemon）经**会话 D-Bus 总线**按需 `dlopen` 装载。

OHOS PC 既没有会话总线、也没有 KDED 装载器，因此：

- 这类 `.so` **编译得出来，但永远不会被加载**——没有装载者；
- 即使手工 `dlopen`，插件内部的会话总线调用（`QDBusConnection::sessionBus()` 等）也没有对端。

典型识别特征（源码级，可直接 grep）：

| 特征 | 位置 | 含义 |
|---|---|---|
| `find_package(KF6DBusAddons ... REQUIRED)` | 顶层 CMakeLists | 需要会话总线 |
| `K_PLUGIN_FACTORY_WITH_JSON(...)` + `*.json` 含 `KDEDModule` | 源码 + 元数据 | 产物是 KDED 插件 |
| `install(... DESTINATION ${KDE_INSTALL_PLUGINDIR}/kf6/kded)` | CMakeLists | 落 KDED 插件目录 |
| `QDBusConnection::sessionBus()` / `org.kde.kded` / `org.kde.kglobalaccel` | 源码 | 运行期依赖会话服务 |

## 根因与可用出路

kwrited 6.7.2 的价值在于：**它把形态选择交给了上游自己的能力宏**，无需我们在平台侧做任何事：

```cmake
# 上游 kwrited 6.7.2 CMakeLists.txt 原文
cmake_dependent_option(BUILD_AS_EXECUTABLE "Whether to build kwrited as executable" OFF
    "KPty_HAVE_UTEMPTER" ON)
```

- `KPty_HAVE_UTEMPTER` 由 **KF6Pty 的包配置**导出；OHOS 侧 `kpty/6.26.0` 是无 UTEMPTER 构建，
  该宏实测为 `FALSE` → 选项被强制为 `ON` → 走**独立可执行程序**分支；
- 该分支**不** `find_package(KF6DBusAddons)`（上游只在插件分支 `if (NOT BUILD_AS_EXECUTABLE)` 里查找，CMakeLists.txt:39-45），也就不需要 `kdbusaddons` 依赖；
- 结论：这是**零补丁**路径 —— 既没伪造能力，也没加平台宏，依赖边界完全由依赖包的真实能力决定。

## 三层处理策略（详见同主题 `strategy.md`）

| 层级 | 适用 | 动作 |
|---|---|---|
| P1 形态切换 | 上游有 `BUILD_AS_EXECUTABLE` 类开关且由能力宏联动（类型 A） | 确认依赖包导出的能力值 → 依赖真值自动落形态，零补丁交付 |
| P2 降级/中性探测 | 无形态开关但存在硬绑定，且功能可独立运行（类型 B） | 中性符号探测 + 回退实现（禁平台宏，R8），必要时把插件功能改造成独立程序 |
| P3 平台不支持 | 功能语义依赖会话总线对端，无独立形态（类型 C） | 如实标 `env_unsupported`（R47/R51），**禁止伪造会话总线/空壳 stub** |

> 特别提醒：**「能编译」不等于「能交付」**。插件形态在无会话平台上编译成功只说明编译链通，
> 产物是无主可加载的死物；判定口径见同主题 `README.md` 的验证矩阵。

## 检测与复现

```sh
# 1) 判定：这份源码是否落在本主题的问题域（类型 A/B/C）
sh knowledge/operations/no-desktop-session-dbus-kded/detect-no-desktop-session-kded-branch.sh <上游源码目录>
# kwrited 6.7.2 实测：TYPE_A_capability_switch=1  TYPE_B_kded_plugin=1  TYPE_C_session_service=0  → RC=0

# 2) 复现「关策略报错 → 开策略生效」（干净环境，私有构建目录）
sh knowledge/operations/no-desktop-session-dbus-kded/reproduce.sh
```

## 与其它条目的关系

- `kpty/6.26.0`（本仓归档）：提供 `KPty_HAVE_UTEMPTER=FALSE`，是本主题类型 A 的能力来源；
- utmp/utmpx 符号缺口（E121）：kpty 侧的历史缺口，与本条正交（本条的形态判定发生在 CMake 配置期）。
