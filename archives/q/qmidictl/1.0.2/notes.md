# qmidictl 1.0.2 — HarmonyOS PC 适配 notes

## 适配日期
2026-10-02

## 上游与交付形态
| 项 | 值 |
| --- | --- |
| 上游 | qmidictl 1.0.2（rncbc / Rui Nuno Capela） |
| 官网 | https://qmidictl.sourceforge.io |
| 源码 | https://download.sf.net/qmidictl/qmidictl-1.0.2.tar.gz |
| sha256 | 5c9e04e560c564b03b6ebd451e310246418b8416f25e6038575bae16c34f4339 |
| 构建系统 | CMake >= 3.15（AUTOMOC/AUTOUIC/AUTORCC） |
| 交付形态 | **application**（bin/qmidictl + share/{applications,icons,metainfo,man}） |
| 上游改动 | 无（`patches: []`） |

## 依赖闭包
| 依赖 | 版本 | 角色 |
| --- | --- | --- |
| qtbase | 6.11.1.3 | Qt6 Core / Gui / Widgets / Network（上游 `find_package(Qt6 COMPONENTS Core Gui Widgets Svg)` + `Network`） |
| qtsvg | 6.11.1.1 | Qt6 Svg 组件（应用图标 qmidictl.svg + .qrc 资源） |

> 版本冲突处置（R35）：`qtsvg/6.11.1.1` 的配方自身钉住 `qtbase/6.11.1.3`，
> 首次图解析报 `Version conflict: Conflict between qtbase/6.11.1.3 and
> qtbase/6.11.1.1`。两个 revision 均以 `conan install --requires=... --build=never`
> 实测二进制齐备（6.11.1.3: 16/16；6.11.1.1: 3/3），按 qtsvg 的钉版取
> `qtbase/6.11.1.3` 消解冲突（**不使用 override 强制回退旧 revision**）。

## conanfile generate() 关键项
- `CMAKE_PREFIX_PATH` = qtbase 包目录 : qtsvg 包目录
- `Qt6_DIR` = `<qtbase>/lib/cmake/Qt6`，`Qt6Svg_DIR` = `<qtsvg>/lib/cmake/Qt6Svg`（E438）
- `CMAKE_MODULE_PATH` = `<qtbase>/lib/cmake/Qt6/platforms`（`Platform/HarmonyOS.cmake` include Linux）
- `CMAKE_CXX_STANDARD=17`（上游 `src/CMakeLists.txt` 固定 C++17）

## 上游测试（R51 三步法）
1. **清点**：解压官方 tarball 后，顶层只有 `CMakeLists.txt / ChangeLog / LICENSE / README / src`；
   `find -type d -name 'test*'`、`find -type f -name '*test*'` 均无命中；顶层与
   `src/CMakeLists.txt` 无 `enable_testing()` / `add_test()`；无 check/test 目标。
   → **上游不提供自动化测试**（清点证据见 `test_package/MANIFEST.yml`）。
2. **可运行环境实际运行**：不适用（无测试入口，无 `make check` 可跑）。上游的
   `--version` / `--help` 由 test_package 消费（见下）。
3. **PR 回填计量**：上游 0 → 适配后 16 项断言（`test_package/test_qmidictl.sh`）。

## 补全测试用例（test_package，消费者视角，真实 exec）
`test_qmidictl.sh` 以 `QT_QPA_PLATFORM=offscreen` 真实运行安装后的二进制：

| 用例 | 断言 |
| --- | --- |
| TP-001 | `<pkg>/bin/qmidictl` 存在 |
| TP-002 | ELF 魔数 `7f454c46` |
| TP-003 | DT_NEEDED 含 libQt6Core/Widgets/Gui/Svg/Network.so.6（5 项） |
| TP-004/005 | `qmidictl --version` 输出含 `1.0.2` / `QmidiCtl` |
| TP-006/007 | `qmidictl --help` 输出含 `--udp-port` / `--interface` |
| TP-008/009/010 | 安装的 `.desktop` / scalable icon / man page 存在 |
| TP-011 | `licenses/LICENSE` 随包安装 |

合计 **16 项断言**。

## 平台注意事项
- OHOS 无 X11/Wayland → `QT_QPA_PLATFORM=offscreen`（qastools/conducteo 先例）；
  上游 `main()` 在建 `QApplication` **之后**才解析 `--version/--help`（`src/qmidictl.cpp:164`），
  所以运行期探针必须在 offscreen 平台下执行。
- OHOS `/system/bin/sh`（mksh）不能执行 ELF → test_package 经 `CONFIG_SHELL` 指向的 bash 包装。
- E077：未签名 ELF 在用户存储路径 exec 被拒（EPERM rc=126），故 `package()` 打包期自签。

## 验证结果

```bash
conan create archives/q/qmidictl/1.0.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build=qmidictl/*
# => qmidictl/1.0.2: Package 'e67e5dcd822742e396f8bd57bda5209a2b2bba2b' created
```

test_package（真实 exec 探针）：

```
== qmidictl consumer probe ==
  [PASS] TP-001 binary present
  [PASS] TP-002 ELF header
  [PASS] TP-003 read DT_NEEDED (libQt6Widgets.so.6 libQt6Svg.so.6 libQt6Network.so.6
                              libQt6Gui.so.6 libQt6Core.so.6 libc++_shared.so libc.so)
  [PASS] TP-003 linked libQt6Core/Widgets/Gui/Svg/Network.so.6（5 项）
  [PASS] TP-004 --version reports 1.0.2
  [PASS] TP-005 --version reports program name
  [PASS] TP-006 --help documents --udp-port
  [PASS] TP-007 --help documents --interface
  [PASS] TP-008 desktop entry installed
  [PASS] TP-009 scalable icon installed
  [PASS] TP-010 man page installed
  [PASS] TP-011 license file packaged
RESULT: PASSED (16/16)
```

## 构建期踩坑记录

| # | 现象 | 根因 | 处置 |
| --- | --- | --- | --- |
| 1 | 图解析 `ERROR: Version conflict: Conflict between qtbase/6.11.1.3 and qtbase/6.11.1.1` | 配方最初钉 `qtbase/6.11.1.1`，而 `qtsvg/6.11.1.1` 自带 `qtbase/6.11.1.3` 钉版 | 跟随 qtsvg 取 `qtbase/6.11.1.3`；两 revision 先以 `conan install --requires=... --build=never` 实测二进制齐备（6.11.1.3: 16/16、6.11.1.1: 3/3），**未使用 override 强制回退** |
| 2 | test_package TP-003（DT_NEEDED 扫描）在 `conan test` 环境里恒为空 → 5 项假失败 | 原实现 `grep ... 2>/dev/null \| sort -u \| tr` 依赖外部工具，而 `env="conanrun"` 会重排 PATH/LD_LIBRARY_PATH；错误又被 `2>/dev/null` 吞掉，表现为"静默空值" | 改为多工具探测（`readelf`/`llvm-readelf` 优先，`grep` 兜底，均试绝对路径）+ 纯 bash 解析，并把工具 rc/错误打进日志；同环境复跑即 `PASSED (16/16)` |

> 记录要点（可复用）：test_package 脚本内**不要**把工具错误重定向到 `/dev/null`
> ——conan 的 `conanrun` 环境与本地 shell 的 PATH 不等价，静默空值会伪装成断言失败。

## 本地验证
- 2026-10-02：`conan create archives/q/qmidictl/1.0.2 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64
  --build=missing --build=qmidictl/*` → 包 `e67e5dcd822742e396f8bd57bda5209a2b2bba2b` created，
  test_package `PASSED (16/16)`（日志 `/storage/Users/currentUser/tmp/qmidictl-create3.log`）。
---

**编译结束**: 2026-10-02 16:24
**最终状态**: built
