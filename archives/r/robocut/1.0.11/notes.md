# robocut 1.0.11 — HarmonyOS PC (aarch64) 适配笔记

## 软件身份

- **软件名**: robocut 1.0.11 = [Timmmm/robocut](https://github.com/Timmmm/robocut)（tag `v1.0.11`，commit `37bb8aa303016326f74fcd7157b7e6d3bf8f28`，2015-06-07）
- **类型**: Qt5 Widgets GUI 应用（`TEMPLATE = app`，非库）：读入 SVG → 经 libusb 批量传输发送到 Graphtec Craft Robo / Silhouette SD-Cameo-Portrait 刻字机/绘图仪
- **许可证**: GPL-3.0-or-later（`Readme.md`: "All code is GPL3 licensed."；`robocut.spec`: `License: GPL-3.0+`）
- **状态**: `built`（采信轮 `conan create` 通过 + test_package PASS；PR 合并且 release upload 确认前不标 published）
- **语言预检（R47）**: task=cpp / detected=cpp，源码 11 个文件 cpp 占 100%

## 编译环境

| 项 | 值 |
|---|---|
| Profile | `ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / clang 15 / libc++ / cppstd17 / Release），host=build |
| 编译器 | `/data/service/hnp/bin/clang` 15.0.4 |
| 构建命令 | `qmake Robocut.pro -spec linux-clang QMAKE_STRIP=` → `make -j2 QMAKE_STRIP=`（in-source） |
| 依赖 | qt5-qtbase/5.15.2.2、qt5-qtsvg/5.15.2.1、libusb/1.0.29（均 ohpcd 已发布 ohos/armv8 预编译包） |
| 产物 | `bin/robocut`（256704 B，aarch64 ELF 64-bit PIE）+ `share/pixmaps/robocut.xpm` |

产物 DT_NEEDED（`llvm-readelf -d`）:
`libusb-1.0.so.0`、`libQt5Svg.so.5`、`libQt5Widgets.so.5`、`libQt5Gui.so.5`、`libQt5Core.so.5`、`libGLESv2.so`、`libc++_shared.so`、`libc.so`

## W0 立项预检

1. **版本可得性**：`git ls-remote --tags https://github.com/Timmmm/robocut.git` 实测含 `refs/tags/v1.0.11` → `37bb8aa3...`；tag 归档 URL 两次独立下载 sha256 **一致**（`4ddd1255cb94f45d403e95aa4e3cea54d2d9d7dfc473cc7b56dab880e90db95a`）。
2. **硬依赖**：`conan list -r=ohpcd` 实查 —— `qt5-qtbase/5.15.2.2`、`qt5-qtsvg/5.15.2.1`、`libusb/1.0.29` 均有 `os=OHOS arch=armv8 clang Release` 预编译包。Qt5 的 svg 模块是**硬依赖**（源码用 `QSvgRenderer`），单包 `qt/5.15.19` 不含（见下）。
3. **平台不可移植判据**：全树 grep `altivec.h` / `mmx.h` / `3dnow` / `emmintrin` / `xmmintrin` / `printf.h` / `register_printf` → **0 命中**；无 ISA 专属路径、无 glibc printf 钩子。上游 2015 年纯 C++/Qt 代码，无内联汇编。

## 适配要点（全部在配方/补丁层）

### 1. `QT += widgets` 缺失（patches/0001）

上游 `Robocut.pro` 只有 `QT += svg`。Qt5 的默认 QT 是 `core gui`（`mkspecs/features/spec_pre.prf:55`），且 `qt_lib_svg.pri` 的 `QT.svg.depends = core gui` 不含 widgets；但源码大量使用 `QApplication`/`QMainWindow`/`QDialog`/`QFileDialog`/`QMessageBox`/`QPushButton`。实测：

```
main.cpp:22:10: fatal error: 'QApplication' file not found
MainWindow.h:24:10: fatal error: 'QMainWindow' file not found
```

`patches/0001-Robocut.pro-add-qt-widgets.patch` 把该行改为 `QT += svg widgets`。交叉证据：Debian bookworm 的 `robocut 1.0.11-1+b2 amd64` 包 `Depends: libqt5widgets5t64`，其 `/usr/bin/robocut` 的 `DT_NEEDED` 实测含 `libQt5Widgets.so.5` —— widgets 是运行期真实依赖。

### 2. 必须走模块化 Qt5（单包 qt/5.15.19 无 svg）

ohpcd 的 `qt/5.15.19` recipe 把 `qtsvg` 放进 `_skipped_modules`（42 个模块 `-skip`），包内**没有 Qt5Svg**。含 `QT += svg` 的工程只能用模块化栈 `qt5-qtbase + qt5-qtsvg`。`qt5-qtsvg/5.15.2.1` 的 recipe 精确声明 `qt5-qtbase/5.15.2`，而带 Widgets 的是 `5.15.2.2`（5.15.2 是 `-no-widgets` 构建）→ 配方用 `self.requires("qt5-qtbase/5.15.2.2", override=True)` 统一（baka 2.0.4 先例）。

### 3. 包内 mkspecs 记录已消失的构建目录 → 可重定位 qmake 视图

制品包内的两个记录面都指向**构建时**绝对路径（conan 缓存 `p/b/<hash>/b` 已被清理）：

```
bin/qt.conf:  [DevicePaths] Prefix=/…/.conan2/p/b/qt5-qa31db92296d5b/p   ← 已不存在
              [Paths] Prefix=<同上> / HostPrefix=<同上>
mkspecs/modules/qt_lib_core.pri:
  QT_MODULE_LIB_BASE = /…/.conan2/p/b/qt5-qa31db92296d5b/b/lib
  include(/…/.conan2/p/b/qt5-qa31db92296d5b/b/mkspecs/modules-inst/qt_lib_core.pri)
```

直接使用包内 qmake 实测报错（首轮）：

```
Cannot read …/mkspecs/modules-inst/qt_plugin_qevdevtouchplugin.pri: No such file or directory
Project ERROR: Unknown module(s) in QT: core gui
```

（`modules-inst/` 里其实**有**这些文件，只是 `include()` 的绝对路径指向已消失的构建目录，逐个读取失败 → 模块变量从未定义。）

修法 `_relocated_qmake()`（qsoas 3.3 先例 + baka 2.0.4 的 svg 模块处理）：

1. 复制 `qt5-qtbase/mkspecs` → `<build>/qt-qmake/mkspecs`；
2. 用 `qt5-qtbase/mkspecs/modules-inst/*.pri`（48 个）**覆盖** `modules/` 下的转发件 —— inst 形态不含任何 `include()`，转发链整体消除；
3. 注入 `qt5-qtsvg/mkspecs/modules-inst/` 的 4 个 svg 模块 .pri（`qt_lib_svg`、`qt_lib_svg_private`、`qt_plugin_qsvg`、`qt_plugin_qsvgicon`）；
4. 剩余 .pri 里残留的 `…/conan2/p/b/<hash>/b` 绝对路径按来源包改写（13 个文件命中）；
5. 复制 `qmake` 到 `<build>/qt-qmake/bin/qmake` 并写一份**指向 package 的** `qt.conf`（`[EffectivePaths] Prefix=..` + `[DevicePaths]/[Paths]/HostPrefix=qt5-qtbase 包目录`）；
6. 反静默守卫：qmake 生成的 Makefile 若仍含 `conan2/p/b/qt…/b/` 历史构建缓存路径即 `ConanInvalidConfiguration`（qsoas 先例；踩过一次过宽正则——`conan2/p/b/[^\s]*/b/` 会命中**本包自身**的构建目录，已收窄为 `qt` 前缀）。

### 4. 外置模块（qtsvg）的 `QT_MODULE_*_BASE` 必须固化为自身包路径

`qt_config.prf` 在加载每个模块 .pri 之前把 `QT_MODULE_{LIB,INCLUDE,HOST_LIB,BIN}_BASE` **统一**设为 `$$[QT_INSTALL_*]`（= qtbase 包）。因此 svg 模块若沿用 inst 形态的 `QT.svg.libs = $$QT_MODULE_LIB_BASE`，`qt.prf` 会生成

```
/…/qt5-qtbase<pkg>/lib/libQt5Svg.so     ← 该路径下没有 libQt5Svg.so
```

链接必失败。故注入 svg 模块时把 4 个 `$$QT_MODULE_*_BASE` 就地替换为 **qt5-qtsvg 包**的 `lib`/`include`/`bin`；改造后链接行实测：

```
… -lusb-1.0 /…/qt5-q9a1e58a3d78a5/p/lib/libQt5Svg.so /…/qt5-q9ce0d1d008b3f/p/lib/libQt5Widgets.so …
```

### 5. libusb 头文件路径与链接

上游 `#include <libusb-1.0/libusb.h>` + `LIBS += -lusb-1.0`。`libusb/1.0.29` 的 `cpp_info.includedirs = ["include/libusb-1.0"]`（面向 `#include <libusb.h>` 的消费者），本工程写法多一层 → 配方用 `CPATH=<libusb>/include`；`-lusb-1.0` 的 `-L` 走 `LIBRARY_PATH=<libusb>/lib`（clang 识别）。

### 6. `QMAKE_STRIP=`（HMDFS 可执行位）

qmake 生成的链接/安装规则默认调用 strip；HMDFS 上被剥离的 ELF 不可执行（baka 2.0.4 / knowthelist 2.3.1 同款坑）。配方在 qmake/make/install 三处均传 `QMAKE_STRIP=` / `STRIP=true`。

## 编译步骤

```bash
conan create . -pr:h="<repo>/ci/conan/profiles/ohos-aarch64" \
               -pr:b="<同上>" -c tools.build:jobs=2
```

- `make install INSTALL_ROOT=<pkg>` 把上游 `INSTALLS += target icon`（`target.path=/usr/bin`、`icon.path=/usr/share/pixmaps`）落到 `<pkg>/usr/…`，`package()` 归一化为 `<pkg>/bin` + `<pkg>/share`。
- 上游 install 规则被真实验证（未走"构建树复制"兜底分支）。

## 上游测试清点（R51）与鸿蒙分栏

- **上游 N = 0**：`tar tzf v1.0.11.tar.gz` 全量 54 条目**无** `test/`、`tests/`、`tst_*`、`*_test*`（`grep -Ei 'test|check'` rc=1 = 0 命中）；`Robocut.pro` 无 `check`/`test` 目标、无 `QT += testlib`；qmake 生成的 Makefile 中 `make check` 是 qmake 默认空目标（`check: first`），不构建也不运行任何用例。⇒ TOTAL=0 / PASS=0 / FAIL=0 / SKIP=0 / NOT_RUN=0，N′=0。
- **鸿蒙特有测试（不计入上游分母）**：`test_package/test.sh` 在 conanrun 环境下**实跑被测包安装的** `bin/robocut`，3 条断言全过（3/3）：
  - A1 二进制在 PATH 中（`command -v robocut`）
  - A2 `robocut --version` rc=0 且输出含 `1.0.11`（实测输出 `1.0.11\n\nCopyright (C) 2015 …`）
  - A3 `robocut --help` rc=0 且输出含 `Usage:`
- 选择 `--version/--help` 而非启动 GUI 的原因：二者在 `main.cpp` 的 `QApplication` 构造**之前**由 `ProgramOptions::GetOpt` 处理并 `exit(0)`，无需显示设备；`main.cpp` 的 `libusb_init()` 也在这之后，故不需要真实切割机。脚本另设 `QT_QPA_PLATFORM=offscreen` 兜底。

## 依赖版本

- qt5-qtbase/5.15.2.2（Core / Gui / Widgets；`override` 统一 qt5-qtsvg 的精确 pin）
- qt5-qtsvg/5.15.2.1（QtSvg 模块，`QSvgRenderer`）
- libusb/1.0.29（`.so` + `include/libusb-1.0/`）

## 已知限制 / 未覆盖

1. **GUI 交互路径未在设备上验证**：`QApplication` + `MainWindow` 需要显示设备/offscreen QPA 插件；本任务只验证到「二进制可执行、自报版本、帮助文本」这一层。完整切割流程还需真实 USB 切割机（本机 `/dev/ttyUSB0`、`/dev/usb/lp*` 等设备节点全缺）。
2. **产物 RUNPATH 内嵌构建期 conan 缓存路径**（`/…/p/qt5-q9ce0d1d008b3f/p/lib`）：运行期由 conanrun/`LD_LIBRARY_PATH` 覆盖；未使用 `CONFIG+=no_qt_rpath` 以保持与上游 qmake 默认行为一致（baka 2.0.4 同形态）。
3. **首次 `conan create` 命中设备 `/dev/shm` 100% 满**：`core.download:parallel` 默认按 `cpu_count()` 起 `ThreadPool` → `Pool.__init__` 的 `SimpleQueue()` → `SemLock` → `OSError: [Errno 28] No space left on device`（verbatim 栈：`conan/internal/graph/installer.py:283` → `multiprocessing/pool.py:196` → `_multiprocessing.SemLock`；`df -h /dev/shm` = `1.0G 1.0G 0 100%`）。用 conan 文档化 CLI 选项 `-cc core.download:parallel=0`（仅本进程覆盖 `global.conf`，不改配方、不改共享配置）串行化下载即通过；依赖已入本地缓存后（无待下载包时 `_download_bulk` 提前 return）**不再需要**该选项，后续 `conan create` 无此问题。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/robocut` | 256704 B | aarch64 ELF 64-bit PIE，动态链接 Qt5/libusb |
| `share/pixmaps/robocut.xpm` | — | 上游 `INSTALLS += icon` 安装的图标 |

## 复现命令（设备可直接执行）

```bash
export HOME=/storage/Users/currentUser
REPO=/storage/Users/currentUser/ws/worktrees/robocut-1.0.11
conan create "$REPO/archives/r/robocut/1.0.11" \
  -pr:h="$REPO/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$REPO/ci/conan/profiles/ohos-aarch64" \
  -c tools.build:jobs=2
```
---

**编译结束**: 2026-10-18 17:00
**最终状态**: built
