# cairo-dock 3.5.0 适配笔记

## 概述

- 上游: https://github.com/Cairo-Dock/cairo-dock-core （GPL-3.0-or-later）
- 版本: 3.5.0（tag 归档，sha256 `67af81683d8178e12f8c2f190936f68658eb1e091d974416a7d1472cc8c7ab63`）
- 形态: C（110 个源文件，`lang-preflight` 实测 detected=c、build_system=cmake）
- 产物: `bin/cairo-dock`（dock 可执行文件）+ `lib/libgldi.so`（GLDI 公共 C API，
  供 cairo-dock-plug-ins 使用）+ 头文件 + `lib/pkgconfig/gldi.pc` + 数据/主题/翻译

## 构建环境（原生 build=host，非交叉编译）

| 项 | 值 |
|---|---|
| OS / Arch | OHOS 6.0 / aarch64（armv8） |
| 编译器 | clang 15（`/data/service/hnp/bin/clang`，经 profile `tools.build:compiler_executables`） |
| CMake | 4.1.2（`/data/service/hnp/bin/cmake`） |
| Conan | 2.29.1（OHOS 适配版） |
| profile | `/storage/Users/currentUser/build_in_harmonyos/ci/conan/profiles/ohos-aarch64` |
| 构建方式 | `conan create`（经 `ohc-run.py conan-verify`），`-pr:h`/`-pr:b` 同一 OHOS profile |

**从不在配方/命令里传 `--host/--build/--target`**（铁律 #0）：本机即目标机，
`CMAKE_SYSTEM_NAME` 由配方设为 `Linux`（与 pan/0.165 等 460+ 配方一致，CMake 无 OHOS platform module）。

## 关键适配点 1：GL 是硬依赖，X11/Wayland/EGL 是可选后端

上游 `CMakeLists.txt:96` 把 GL 放进 **REQUIRED** 的模块列表：

```cmake
set (packages_required "glib-2.0 gthread-2.0 cairo librsvg-2.0 dbus-1 dbus-glib-1 libxml-2.0 gl glu libcurl")
pkg_check_modules ("PACKAGE" REQUIRED "${packages_required_semicolon}")
...
pkg_check_modules ("GTK" REQUIRED "${gtk_required}>=3.4.0")
```

而 X11 / Wayland / EGL 的探测**没有 REQUIRED**（X11 段 `pkg_check_modules("X11" x11)`、
Wayland 段 `pkg_check_modules("WAYLAND" wayland-client)`、EGL 段 `pkg_check_modules("EGL" egl)`），
缺失即把 `with_x11/with_wayland/with_egl` 置 no。实测配置摘要（本机真实构建输出）：

```
--  * GTK version         : 3 (3.24.38.1)
--  * With X11 support    : no
--  * With X11 extensions : no ()
--  * With GLX support    : no
--  * With Wayland support: no
--  * With EGL support    : no
--  * Crypt passwords     : no
```

本包在配方里显式 `-Denable-x11-support=OFF -Denable-wayland-support=OFF -Denable-egl-support=OFF`：
OHOS 既没有 X server 也没有 Wayland compositor，且 ohpcd 的 gtk3 是 **broadway 后端**
（`x11_backend=false / wayland_backend=false / broadway_backend=true`，见 gtk/3.24.38.1 配方），
GDK 不定义 `GDK_WINDOWING_X11`；显式关闭可避免误开 GLX/X11 路径后去拉 Xcomposite/Xrandr 等头文件。

> 注意：**"X11 可选"只在 CMake 层成立**——`src/cairo-dock-gui-advanced.c` 无条件依赖
> `gdk/gdkx.h`，与 `-Denable-x11-support=OFF` 无关，必须另打源码补丁（见"源码补丁 0002"
> 与"关键适配点"）。

### `gl` / `glu` 两个模块怎么来的

OHOS 无桌面 `libGL.so`：ohpcd 的 `mesa/24.3.4.1`（glu/9.0.3 所 pin 的版本）只交付
`libOSMesa.so` + `libglapi.so` + GL 头文件（`include/GL/gl.h|glext.h|glx.h|osmesa.h`），
不提供 `gl.pc`。因此 `generate()` 里把 mesa 包自带的 `osmesa.pc` 复制为 **`gl.pc`**，
`Name:` 改为 `gl`、`prefix=` 改写为真实包目录（同一手法 glu/9.0.3 配方对 `osmesa` 模块做过）：
`Libs: -L${libdir} -lOSMesa`。

`libOSMesa.so` 导出全部桌面 GL 入口点（softpipe 软件渲染，无 X11/Wayland/DRM），
与 coin3d/4.0.10-src 在 OHOS 上使用同一个 GL provider。

`glu.pc` 由 `PkgConfigDeps` 从 `glu/9.0.3`（`pkg_config_name=glu`）生成，`-lGLU`；
`mesa.pc`（`-lOSMesa`）随 `Requires:` 链一并生成。

## 关键适配点 2：`dbus-1` 模块名（转发别名 .pc）

`dbus/1.14.10.1` 配方没有声明 `pkg_config_name`，`PkgConfigDeps` 于是只生成 **`dbus.pc`**；
上游要的是上游模块名 **`dbus-1`**。故 `generate()` 写一个转发型别名：

```
Name: dbus-1
Version: 1.14.10.1
Requires: dbus
```

（E321/E527 记录的 alias-pc 手法；flags 全部由 `dbus.pc` 提供，别名不带自己的 flags。）

## 关键适配点 3：依赖图必须"对齐版本"，否则会触发依赖源码重编（package_id 陷阱）

先把两组事实摆出来（`conan graph info` 实测）：

| 候选 | gtk/3.24.43 + librsvg/2.62.3.1.1 | gtk/3.24.38.1 + librsvg/2.62.3 |
|---|---|---|
| cairo-gobject | gtk pin **1.18.4.2** / librsvg pin **1.18.4.3** → 冲突 | 双方都 pin **1.18.4** ✓ |
| pango | 1.50.14.1.1 / 1.50.14.1.1 | 双方都 1.56.4 ✓ |
| gdk-pixbuf | 2.44.6.1 / 2.44.6.1 | 双方都 2.44.6 ✓ |
| 图结果 | 任选一边 override → 另一边的 **package_id 变化** → 该依赖二进制"缺失"，CI 会从源码重建（gtk 或 librsvg-rust），或直接红 | 全节点 `Download`/`Cache`，**无 `Build`/`Missing`** |

`gtk` 把 cairo-gobject 声明为 `transitive_headers=True`（embed，full 版本参与 package_id），
所以任何 cairo-gobject 版本改动都会改 gtk 的 package_id；反过来 librsvg 的 package_id 同样
跟着变（实测：同一 cairo-gobject 取 .2 时 librsvg 变 `Missing`，取 .3 时 gtk 变 `Missing`）。
同仓库 `libcryptui/3.12.2` 的注释记录过同一类教训（"消费者侧不再写 override —— 那会把
dbus-glib 的 package_id 从已发布值改掉 …结果就是「依赖二进制缺失」红灯"）。

**结论**：本包选择 `gtk/3.24.38.1` + `librsvg/2.62.3` 这一**互相锁定**的已发布组合，
除 `dbus/1.14.10 → 1.14.10.1`（仅适配后缀不同，`semver_mode` 下不改变 package_id）外
**不写任何 override**。

另：`dbus/1.14.10.2+` 打开了 `DBUS_WITH_GLIB` → `requires glib/2.88.3`，与 GTK 树的
`glib/2.84.0.1` 冲突；故对齐到 `dbus/1.14.10.1`（与 `dbustest/19.04.0.1` 同一组合）。

## 关键适配点 4：CMake 4 拒绝 `cmake_minimum_required (VERSION 2.6)`

上游 `CMakeLists.txt` 声明 2.6，CMake ≥ 4 直接拒绝（"Compatibility with CMake < 3.5 has been removed"）。
按仓库既有做法（615 个配方、知识条目 **E187: add-cmake-flag**）注入
`CMAKE_POLICY_VERSION_MINIMUM=3.5`，**不改上游源码**。

## 关键适配点 5：`localtime_r` 需要 POSIX 特性宏（musl）

上游若干 `src/*.c`（`gldit/cairo-dock-themes-manager.c:25`、`cairo-dock.c`、
`gldit/cairo-dock-packages.c` …）用 **glibc 内部宏** `#define __USE_POSIX` 再
`#include <time.h>` 去取 `localtime_r()`——那是 glibc 私有约定，musl 的
`features.h` 不认；叠加项目自带的 `-std=c99`（严格 ANSI）隐藏了 POSIX 声明，于是：

```
cairo-dock-themes-manager.c:262:2: error: call to undeclared function 'localtime_r';
ISO C99 and later do not support implicit function declarations [-Werror,-Wimplicit-function-declaration]
```

按仓库既有做法（add-cflags / feature-test-macro 类，知识 E032 同族）在配方里
**全构建期**注入 `-D_POSIX_C_SOURCE=200809L`（`CMakeToolchain.preprocessor_definitions`），
让 `features.h` 打开 POSIX.1-2008 声明；实测源码不使用 GNU/BSD-only 函数
（无 `strcasestr/memmem/strsep/asprintf/vasprintf/strndup`），故全局开启无副作用。

## 关键适配点 6：链接缺 `g_libintl_*` —— 对生成的 `glib-2.0.pc` 追加 `-lintl`

`glib/2.84.0.1` 以 **Windows 式 proxy `<libintl.h>`** 交付（`include/libintl.h`，
`#define gettext g_libintl_gettext`、`dgettext→g_libintl_dgettext` …），同名包内
`lib/libintl.so.8` 导出这些 `g_libintl_*` 符号；`glib/gi18n.h` 的 `_()` 宏走这条链。

- 上游自带 `glib-2.0.pc` 的 `Libs` 含 `-lintl`，但 `PkgConfigDeps` 依据 glib 配方的
  `cpp_info` **重建** `.pc`，丢掉 `-lintl`（生成物只有 `-lglib-2.0 -lm -lpthread -ldl`）；
- 上游自己的守卫 `check_library_exists(intl libintl_gettext "")`（CMakeLists.txt:193）
  也**不成立**：glib 的 libintl.so 导出的是 `g_libintl_gettext`，不是 `libintl_gettext`
  → `LIBINTL_LIBRARIES` 为空 → 全程无 `-lintl`；
- 结果：链接 `cairo-dock` 可执行文件时报
  `ld.lld: error: undefined symbol: g_libintl_gettext`（`libgldi.so` 因共享库允许未定义
  先过，可执行文件以 `--no-allow-shlib-undefined` 拦住）。

修复：`generate()` 里对生成的 `glib-2.0.pc` 的 `Libs:` 行追加 `-lintl`（仅当 glib 包内
确有 `lib/libintl.so`）。pkg-config 会把 `-lintl` 带进 `PACKAGE_LIBRARIES` /
`GTK_LIBRARIES`——三个 target（`gldi`、`cd-Help`、可执行文件）都链它，且各
`CMakeLists.txt` 的 `link_directories()` 都在建 target 之前（glib 的 `-L` 已在线上）。
同型先例：`at-spi2-core/2.60.5`、`ayatana-ido/0.10.4`（"对 .pc 追加 -lintl"）。
实测产物 `DT_NEEDED` 出现 `libintl.so.8`（见 test_package 探针），证明链接期解析正确。

## 源码补丁（2 个，`refresh-patch --auto` 生成）

`patches/0001-Help-src-CMakeLists.txt.patch` — 把 `Help/src/CMakeLists.txt` 的
`link_directories()` 块移到 `add_library()` **之前**。

- 根因：CMake 的 `link_directories()` 只对**在其之后创建**的 target 生效；上游把
  `add_library(cd-Help …)` 写在 `link_directories(...)` 前面，于是 Help 插件链接线上
  **一个 `-L` 都没有**。发行版里 GTK3/GL 都在默认链接路径 → 看不出来；Conan 布局下必炸：
  `ld.lld: error: unable to find library -lrsvg-2 / -lturbojpeg / -lzstd / -lwebp / -lpango-1.0 …`。
- 补丁只调整 CMake 调用顺序，不改变链接的库集合（`src/CMakeLists.txt`、`src/gldit/CMakeLists.txt`
  的顺序本来就是对的，无需改动）。
- 生成方式：改 `.work` 源文件 → `ohc-run.py refresh-patch cairo-dock 3.5.0 --auto`
  （orig/work hash: `2b169b261e6321d7` / `8d8148346c419d5e`），非手写 diff。

`patches/0002-src-cairo-dock-gui-advanced.c.patch` — 把
`src/cairo-dock-gui-advanced.c` 的 `#include <gdk/gdkx.h>` 与 `_check_group_button()`
里的 X11 专属「活动窗口」判定用 `#ifdef GDK_WINDOWING_X11` 包起来。

- **"X11 可选"在源码层被证伪**：CMake 层 X11 确实是可选后端
  （`pkg_check_modules("X11" x11)` 无 `REQUIRED`，`enable-x11-support` 只是默认开），
  但 `src/CMakeLists.txt` 的 `cairo_dock_SRCS` **无条件**包含
  `cairo-dock-gui-advanced.c`，而该文件第 25 行**无条件** `#include <gdk/gdkx.h>`、
  第 1001 行**无条件**用 `GDK_WINDOW_XID`。ohpcd 的 `gtk/3.24.38.1` 是纯 broadway
  后端（`gdkconfig.h` 无 `GDK_WINDOWING_X11`，不含 `gdk/gdkx.h`），因此即使
  `-Denable-x11-support=OFF` 也必炸：`fatal error: 'gdk/gdkx.h' file not found`。
- 其余 X11/GLX/EGL/Wayland 文件都有正确的 `#ifdef HAVE_X11 / HAVE_GLX / HAVE_EGL /
  GDK_WINDOWING_WAYLAND` 守卫（全树 grep + 实测：`gldi`/`implementations`/`cd-Help`
  在旧补丁下已能编过），只有这一个文件漏了。
- 非 X11 回退用可移植的 `gtk_window_is_active(GTK_WINDOW(s_pMainWindow))`（broadway
  等所有 GDK 后端都提供），保持"配置窗口失去激活即收起预览"的原意；X11 GTK 上
  走原路径、行为不变。guard 手法与 `libcanberra-gtk3/0.30 patches/0007` 同型。
- 生成方式同上（同一次 `refresh-patch --auto`；orig/work hash:
  `2b169b261e6321d7` / `e43576d9c49bbd2c`），非手写 diff。

## 上游测试清点与执行（R51）

**结论：上游可运行自动化测试 N = 0 / N′ = 0。**逐项证据见 `test_package/MANIFEST.yml`，要点：

1. 构建系统不注册任何测试：全树 `grep -rn "enable_testing|add_test|include(CTest)" --include=CMakeLists.txt` = **0 命中**。
   顶层只 `add_subdirectory(src data po)` + `Help`。`ctest` 无测试可跑（会把 "No tests were found" 当作失败退出）。
2. `tests/` 是 **13 个 .py**（11 个 `Test*.py` 场景 + `main.py` 运行器 + `config.py`），
   不是 C 测试程序，且逐项依赖：运行中的 dock（X 显示）+ D-Bus + `xdotool`（3 个文件里出现）
   + 可被启动的 `gnome-calculator` 等。
3. 决定性证据：所有脚本 `from CairoDock import CairoDock`，而**官方 3.5.0 归档里没有 `CairoDock.py`**
   （`tar tzf … | grep -ci cairodock.py` = 0）→ 上游该套件在发布包中即为不完整状态，`python3 tests/main.py`
   在 import 阶段就失败。

因此本包的"运行证据"由 `test_package/` 的消费者探针提供（真实链接 + 真实 API 调用 + 加载器闭包探测），
而不是把上游跑不了的脚本标成 pass。

## 验证结果

数字由最终日志复算。

### 上游测试（R51）：TOTAL = PASS + FAIL + SKIP + NOT_RUN

| 项 | 值 | 证据 / 原因 |
|---|---|---|
| 构建系统注册的测试（N） | **0** | 全树无 `enable_testing()`/`add_test()`/`include(CTest)`；顶层只 `add_subdirectory(src data po)` + `Help` → `ctest` 无测试可跑（退出 8）|
| 归档内 GUI 脚本（12 个 `tests/*.py`） | **NOT_RUN = 12** | 需显示服务 + D-Bus + `xdotool`，且全部 `from CairoDock import CairoDock`，而 3.5.0 发布归档不含 `CairoDock.py` → import 阶段即失败。逐项理由见 `test_package/MANIFEST.yml` |
| PASS / FAIL / SKIP | 0 / 0 / 0 | 无可运行项 |

（"上游无可运行测试"由清点证据支撑，未把不可运行脚本记成 pass。）

### 消费者 / `test_package`（真实 API + 断言）

| 项 | 值 |
|---|---|
| TOTAL | **25** |
| PASS | **25** |
| FAIL | 0 |
| SKIP | 0 |
| NOT_RUN | 0 |

覆盖：`bin/cairo-dock` 存在/可执行/ELF/AArch64；`cairo-dock` 与 `libgldi.so.3` 的 `DT_NEEDED`
闭包（含 GTK3/Cairo/GLib、桌面 GL 提供者 `libOSMesa.so.8`、`libintl.so.8`）；安装的
`gldi-config.h` 报 `GLDI_VERSION 3.5.0` 且未定义 `HAVE_X11/GLX/WAYLAND/EGL`；
`cairo-dock --version` 走到 GDK 显示初始化（无头环境预期，加载器闭包全解析）；
消费者程序 `test_cairo_dock` 经 pkg-config 模块 `gldi` 链接 `-lgldi` 并调用
`cairo_dock_get_version_from_string()` / `cairo_dock_string_contains()`（5 项断言全 OK）。
逐条计数见 `test_package/MANIFEST.yml` 的 `assertion_count`。

### 门禁

| 门禁 | 结果 | 证据 |
|---|---|---|
| `conan-verify`（G0/G1/G2/G3/G4） | **PASS** | `reports/conan-verify-report.md`（G2 `conan create` 干净构建成功，test_package 执行）|
| CI 同构 `ci/conan/build_and_test.sh` | **PASS** | `CI_PACKAGES=archives/c/cairo-dock/3.5.0`，job `cairo-dock-ci-20261016-10`：G0/KC/JC/L0/L1/L4/L5 pass，L2 skip，Total 1 / Success 1 / Failed 0 |
| 独立审查（W4/R52） | **未执行** | 交主会话：本任务只做到本地候选 + 门禁 |

### 已知 CI 启发式误报（如实记录）

CI 的 `L1c` 只用 `grep -E "make.*check|ctest|meson test|pytest"` 扫 build 日志。本包
`patches/0002` 的 `patch_description` 里 "**C**Make-level ... pkg_**check**_modules" 恰好
构成 `make.*check`，于是 `L1c` 打印"上游官方测试已执行"——这是**误报**：本包上游
N=0（见上表与 `MANIFEST.yml`，`upstream_test_in_build: false`）。未改动描述文本来
"躲"启发式；此处如实说明，供审查者核对。CI 自身也把 `L2`（版本/帮助 smoke）标为
`skip: cairo-dock version/help failed`（无头无显示，非阻断）。

## R40 说明（GUI 深度适配边界）

cairo-dock 是 GTK3 桌面 dock：真正显示需要显示会话（OHOS 上即 broadway 服务 + 浏览器，
且 gtk4-broadwayd 在 OHOS 上因签名约束不可执行，见知识条目 E471）。
CI/本机无显示会话，故 GUI 交互行为属于**部分验证**：本包验证到
①产物存在且为 AArch64 ELF、②DT_NEEDED 闭包完整（含 `libgldi.so.3`、GTK3/Cairo/GLib 与桌面 GL provider）、
③安装的 `gldi-config.h` 版本与"可选后端未启用"两项事实、④可执行文件能启动到 GDK 初始化（加载器全闭包可解析）、
⑤消费者侧真实链接并调用 `libgldi` 导出 API。
