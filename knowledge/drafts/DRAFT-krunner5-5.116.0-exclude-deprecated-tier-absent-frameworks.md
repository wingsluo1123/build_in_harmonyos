# DRAFT：KF5 库 deprecated API 档牵连链外框架的整档消解（EXCLUDE_DEPRECATED_BEFORE_AND_AT）

- **来源**：krunner5 5.116.0 适配（2026-10-16，KDE Frameworks 5.116）
- **严重度**：2（不设档位配置即中止；档位选错则 API 面无谓缩减）
- **分类**：cmake, kde-frameworks, cross-compile

## 问题

KRunner 5.116 源码中有一大档 deprecated API —— KPluginInfo/KService 体系、
`Plasma::Package`、KProtocolInfo —— 分别链接 `KF5::Service`、`KF5::Plasma`、
`KF5::KIOCore`，而受限链条（ohpcd）没有这三个包。

档位变量默认值 0（= 全部弃用 API 启用）。此时根 `CMakeLists.txt` 第 61–65 行：

```cmake
if(NOT EXCLUDE_DEPRECATED_BEFORE_AND_AT STREQUAL "CURRENT" AND
   EXCLUDE_DEPRECATED_BEFORE_AND_AT VERSION_LESS 5.91.0)
    find_package(KF5KIO ${KF_DEP_VERSION} REQUIRED)
    find_package(KF5Service ${KF_DEP_VERSION} REQUIRED)
    find_package(KF5Plasma ${KF_DEP_VERSION} REQUIRED)
else()
    set(KF5Plasma_FOUND 0)
endif()
```

守卫为真 → 三个 `find_package(... REQUIRED)` 激活 → configure 在第一个缺失包
（KF5Service）处中止。改源码删守卫侵入上游（违反 P005），而这些老 API 本来就不是
适配目标所需的——上游为此提供了官方旋钮，应当用它。

## 根因与机制

上游用 ECM 弃用档位机制把「老 API 组」按弃用版本切块；配方一个 CMake 值
`EXCLUDE_DEPRECATED_BEFORE_AND_AT=5.91.0` 同时作用于三层：

1. **配置层** `CMakeLists.txt:61-68`：三包 `find_package` 都在
   `… VERSION_LESS 5.91.0` 守卫内。取 5.91.0 落入 else 分支：三包根本不查找，
   并 `set(KF5Plasma_FOUND 0)` 关掉下游 Plasma 分支。
2. **链接层** `src/CMakeLists.txt:71-80`：`KF5::Service`/`KF5::Plasma`/
   `KF5::KIOCore` 链接块同一守卫（行内注释明示用途：KPluginInfo /
   plasma/version.h / KProtocolInfo），整块摘除。
3. **头文件层** `src/CMakeLists.txt:47-54`：`ecm_generate_export_header(...)`
   把档位值写入导出头。`src/abstractrunner.h:24-29` 的
   `#if KRUNNER_ENABLE_DEPRECATED_SINCE(5, 91)` 翻转为假 → 走
   `#include <KPluginFactory>` 分支，`<KPluginInfo>`/`<KService>` 不再被包含，
   kservice 完全不进依赖图；`:31-34` 的 plasma 头（(5,65) 档）同关。

附带：`src/declarative`（弃用的 org.kde.runnermodel QML 插件）由
`VERSION_LESS 5.0.0` 守卫 → 任何 ≥5.0.0 的档位值都不构建。

### 档位选择规则（可复用的核心）

**取恰好摘掉链外依赖的最小档位值**，且必须与源码现存守卫常量精确对齐。

- krunner5 的链外三包集中在 5.91.0 档（值 <5.91.0 即包含）→ 最小充分值 = 5.91.0；
- 值取太低（默认 0）→ 守卫为真 → 链外 `find_package` 激活 → 配置失败；
- 值取太高（`CURRENT`）→ 连带关闭链上**完全可满足**的更高档：krunner5 的 5.94 档
  （`abstractrunner.h:15-21` 的 `KConfigGroup`/`QIcon` 实体包含，对应
  `src/CMakeLists.txt:81-86` 在 <5.94.0 时把 `Qt::Gui`/`KF5::ConfigCore` 链接为
  PUBLIC）——无谓缩小 API 面并把链接可见性 PUBLIC→PRIVATE。

上游同一个档位值同时驱动 CMake 守卫与导出头宏，两者天然一致；手改源码删守卫会
打破这种一致性且违反 P005。

## 修法

配方 `configure` 参数列表加一行，无任何源码补丁：

```
EXCLUDE_DEPRECATED_BEFORE_AND_AT=5.91.0
```

## 验证（2026-10-16，OHOS PC arm64 真机，conan 2.29.1）

```
$ conan create archives/k/krunner5/5.116.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

- 链条缺 KF5Service/KF5KIO/KF5Plasma 三包，configure **全程未查找、直接通过**
  （档位生效的直接证据）；
- 5.91.0 档位下上游测试注册 N=6 目标 / 27 QTest 槽位（`autotests/runnercontexttest.cpp`
  因 `VERSION_LESS 5.76.0` 守卫不注册）；本机无 dbus 工具链，无总线分支
  ctest 3/3（`100% tests passed, 0 tests failed out of 3`）；
- test_package 31/31；conan-verify G1–G4 + L2/L4/L5 全 PASS。

## 如实声明（API 面损失）

本构建**不包含**：`KPluginInfo` metadata()、`KService::Ptr loadRunner`、
`Plasma::Package` 相关弃用 API。基于 `KPluginMetaData`/`KPluginFactory` 的现代
API 完整可用（test_package 全量覆盖后者）。

## 适用面

- 任何 KF5 系统库其 deprecated 档牵连链外框架者——受限链条上适配 Tier 2/3 库的
  高频问题类；
- 同样适用于上游把多组老 API 按版本切块、多档并存的场景（krunner5 = 5.91.0 档 +
  5.94.0 档）：逐档判断「链上可否满足」，只摘链外档；
- 手法对照：Qt5 供给断点走桥接
  （[DRAFT-E5xx-qt5-conan-split-cmake-bridge](DRAFT-E5xx-qt5-conan-split-cmake-bridge.md)），
  KF6 依赖受限走补丁式裁剪
  （[DRAFT-E5xx-ktextaddons-kio-qtkeychain-baseline-pruning](DRAFT-E5xx-ktextaddons-kio-qtkeychain-baseline-pruning.md)），
  本条是第三类：**配置期档位**——零补丁、纯上游官方机制。

## 边界

- 档位 = API 面缩减，不是编译开关：被排除的 API 对上层应用不可用，必须在
  MR/notes 如实声明，不得静默降级；
- 不要为「保险」取 `CURRENT`：会把链上可满足的更高档（5.94）也关掉；
- 档位是上游 ECM 官方机制，与平台条件编译宏无涉（不要把两者混为一谈）；
- 机制可逆：未来链条补上相应包且确需老 API 时，把档位值下调回 <5.91.0 即恢复。
