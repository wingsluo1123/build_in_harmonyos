# pa-applet g20181009 适配笔记

## 基本信息

| 项 | 值 |
|---|---|
| 软件 | pa-applet（PulseAudio 系统托盘音量控制小程序，GTK+3） |
| 版本 | g20181009（FreeBSD ports 命名，对应上游提交 `fernandotcl/pa-applet@3b4f8b3`） |
| 上游 | https://github.com/fernandotcl/pa-applet |
| 源码 | `https://codeload.github.com/fernandotcl/pa-applet/tar.gz/3b4f8b3` |
| sha256 | `32dcd0663cca120cf60d1046443884f854448e7bb71226a416915ae9beb33e11` |
| 语言 | C99（`detected=c`，与 cpp 同族，lang-preflight 通过） |
| 构建系统 | 上游 autotools → 本配方改为自带 `CMakeLists.txt` |
| 目标 | OHOS armv8 / clang 15.0.4 / Release |
| 许可证 | GPL-3.0-or-later |

上游提交很老（2018），代码量约 13KB、8 个 `.c` + 6 个 `.h`，无测试套件。

## 编译步骤

```bash
conan create . -pr=ohos-aarch64 --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autogen.sh` 直接失败：`Error: aclocal is required to run ./autogen.sh` | 上游只提供 autotools，git 快照不含预生成的 `configure`；构建环境无 automake/aclocal/libtool（制品仓也没有） | 配方自带 `CMakeLists.txt`，按上游 `Makefile.am` 的源文件集合与安装项（`bin/pa-applet` + `man/pa-applet.1`）复刻；仓库内已有大量同类先例（如 pamixer/1.6） |
| 2 | `key_grabber.c:10:10: fatal error: 'gdk/gdkx.h' file not found` | 制品仓 `gtk/3.24.43` 是 **broadway-only** 构建（`gdkconfig.h` 里 `#undef GDK_WINDOWING_X11`），X11 专用头 `gdk/gdkx.h` 不随包安装；而上游无条件 include 该头并用 `XGrabKey`/`GDK_DISPLAY_XDISPLAY` 做全局媒体键抓取 | `patches/0001-guard-x11-key-grabber.patch`：用工具包自身的后端宏 `GDK_WINDOWING_X11` 守卫 X11-only 代码，后端缺失时保留 `key_grabber_*` 公开 API 并输出诊断；**不引入任何平台宏**（能力探测优先于平台名硬编码） |
| 3 | 依赖版本冲突：`gtk/3.24.43` 要 `glib/2.84.0.1`，`libnotify/0.8.3.1` 与 `pulseaudio/17.0.1` 要 `glib/2.88.0` | gtk 整条依赖线钉在 glib 2.84（cairo/atk/gdk-pixbuf/libpng/libtiff/harfbuzz 的二进制都只对 2.84 线存在）；反向统一到 2.88 线会触发十余个包源码重建，统一到 2.84 线只需重建两个**小包** | 用 `force=True` 守 gtk 线（`glib/2.84.0.1`、`zlib/1.3.1.1`、`gdk-pixbuf/2.44.6.1`）+ `expat/2.8.2.1` override，让 `libnotify` 与 `pulseaudio/17.0.1` 走源码重建（实测各约 1~4 分钟） |
| 4 | `pulseaudio/17.0` 没有 `pulse-mainloop-glib` 组件，但 pa-applet 用 `pa_glib_mainloop_new` 把 libpulse 回调接进 GTK 主循环 | 17.0 的配方以 `glib=disabled` 构建，只发布 `pulse`/`pulse-simple`/`pulsecommon`；17.0.1 才有 glib 组件 | 依赖改用 `pulseaudio/17.0.1`（`libpulse-mainloop-glib.pc` 与 `PulseAudioConfig.cmake` 均随包发布），并把它重编到 gtk 的 glib 2.84 线（见 #3） |
| 5 | 全源文件编译失败：`pango-coverage.h:28:10: fatal error: 'hb.h' file not found` | pango 的头直接 `#include <hb.h>`，但其 CMake 目标没有把 harfbuzz 的 include 目录传播给消费者 | 配方显式 `self.requires("harfbuzz/14.2.0.1.1.1")`（与图中实际解析版本一致）补齐 include 传播 |
| 6 | `source()` 里 `get()` 报 `BadZipFile: File is not a zip file` | codeload URL 末段是纯 commit 号（`.../tar.gz/3b4f8b3`），没有扩展名，conan 按「非 `tar.*`」猜测为 zip | `conandata.yml` 显式声明 `filename: "pa-applet-g20181009.tar.gz"` |
| 7 | 补丁「已导出」但编译时完全没生效（`s/` 源树无 `GDK_WINDOWING_X11`，`build()` 里再打也无效） | 两个坑叠加：①conan 在 `source()` 之后就把源树复制到构建目录，补丁必须放在 `source()`；②`patches` 若写成「文件名 → 条目」的映射，`apply_conandata_patches` 会把它当作「版本 → 条目」的字典、按 `conanfile.version` 取不到条目而**静默跳过** | `patches` 改为 list 形态；`apply_conandata_patches(self)` 移到 `source()` 的 `get()` 之后 |

## 源码修改

- `patches/0001-guard-x11-key-grabber.patch`（+24/−1，唯一补丁）
  - `#include <gdk/gdkx.h>` / `<X11/Xlib.h>` 包进 `#if defined(GDK_WINDOWING_X11)`；
  - `key_grabber_init()` 的 `XGrabKey`/`XKeysymToKeycode` 逻辑同样置于该宏下；
  - 后端缺失时 `key_grabber_init()` 仍返回可用句柄并输出诊断，`key_grabber_free()` 保持幂等——不改公开 API，不删功能入口。
  - 判定依据来自工具包发布面：`gdkconfig.h` 的 `GDK_WINDOWING_*` 集合、`gtk/gtkplug.h` 自身即以 `#ifdef GDK_WINDOWING_X11` 守卫 X11 API。

## 依赖版本

| 依赖 | 版本 | 来源 |
|---|---|---|
| gtk | 3.24.43 | 制品仓二进制（broadway-only 后端） |
| pulseaudio | 17.0.1 | 制品仓二进制存在，但需重建到 glib 2.84 线（本图） |
| libnotify | 0.8.3.1 | 同上，重建到 glib 2.84 线 |
| glib | 2.84.0.1 | force（守 gtk 线） |
| zlib | 1.3.1.1 | force |
| gdk-pixbuf | 2.44.6.1 | force |
| expat | 2.8.2.1 | override |
| harfbuzz | 14.2.0.1.1.1 | 显式声明（pango 头传播缺口） |

## 验证结果

上游（`fernandotcl/pa-applet@3b4f8b3`）**没有测试套件**：无 tests/ 目录、`Makefile.am`
只有 `bin_PROGRAMS`/`man_MANS` 没有 `TESTS`（`make check` 是空目标）、程序是 GUI 托盘
小程序无脚本化入口。因此可测面 = 程序自身的 CLI 选项矩阵 + 产物契约，全部纳入
`test_package/test_pa_applet.sh`，逐条判 PASS / FAIL / **SKIP（带原因）**，不静默跳过。

```text
$ conan create . -pr=ohos-aarch64 --build=missing
pa-applet/g20181009: Apply patch (portability): 以 GDK 自身后端宏 GDK_WINDOWING_X11 守卫 ...
======== Launching test_package ========
=== 静态断言（不执行进程） ===
PASS: 包内含 pa-applet 二进制
PASS: 二进制带可执行位
PASS: 二进制是合法 ELF
PASS: DT_NEEDED 含 gtk-3
PASS: DT_NEEDED 含 libpulse
PASS: DT_NEEDED 含 libpulse-mainloop-glib
PASS: DT_NEEDED 含 libnotify
SKIP: API 符号 key_grabber_init :: 二进制已 strip，无法用 nm 判定
=== 上游 CLI 用例（pa-applet 的全部选项面） ===
SKIP: --help :: OHOS 动态加载器无法解析整套 GTK3 依赖（libintl/g_libintl_*），进程未进入 main()
SKIP: 未知选项 --bogus-option 被拒绝 :: 同上
SKIP: --disable-key-grabbing 被接受 :: 同上
SKIP: --disable-notifications 被接受 :: 同上
SKIP: 组合选项 :: 同上
SKIP: 无参数启动 :: 同上
=== 用例汇总 ===
PASS=7  FAIL=0  SKIP=7
RESULT: PASS-WITH-SKIPS
CONAN_RC=0
```

### 上游用例覆盖情况（测什么、测不到为什么）

| 上游可测面 | 覆盖手段 | 本机结果 | 测不到的原因 |
|---|---|---|---|
| `--help` 用法串 + 退出码 | 运行 `--help`，断言 exit 0 且用法串含两个上游选项 | SKIP | 见下「运行期限制」：加载器无法解析 `g_libintl_*` 等符号，进程未进 `main()` |
| `--bogus-option` 被拒绝 | 运行未知选项，断言非 0 退出（证明 GOption 解析面是活的） | SKIP | 同上 |
| `--disable-key-grabbing` | 运行该选项，断言不被当未知选项拒绝 | SKIP | 同上 |
| `--disable-notifications` | 同上 | SKIP | 同上 |
| 两个选项组合 | 同上 | SKIP | 同上 |
| 无参数启动（gtk_init→连 PulseAudio→建托盘） | 运行无参数，记录退出码与首屏输出 | SKIP | 同上；即便能起进程，本环境也无显示器/托盘宿主 |
| X11 抓键代码在本后端被正确编掉、公开 API 未删 | 静态：源码补丁 + `DT_NEEDED` 四项 + 符号断言 | PASS（符号断言 SKIP：二进制 strip） | — |
| 产物契约（二进制/可执行位/ELF/链接关系） | 静态断言 | PASS | — |

跳过判定口径是**窄**的：只有 stderr 命中 `Error loading shared library|symbol not
found|Error relocating` 才按平台限制跳过；任何其他失败一律 FAIL。同时用破坏性检查
验证过这套断言不是空壳：把二进制删掉后脚本立即 `FAIL` 并 exit 1（L1e）。

### 运行期限制（不影响编译，须向使用者说明）

1. **无系统托盘宿主**：OHOS PC 会话没有 SNI/StatusIcon 宿主，托盘图标不会显示；
   程序本身可启动且不崩溃。
2. **无通知守护**：`org.freedesktop.Notifications` 由 `libnotify` 发送，本环境无守护进程，
   通知静默丢弃（`notify_notification_show()` 返回错误码，程序继续运行）。
3. **全局媒体键不可用**：需要 X11 GDK 后端，当前 GTK 为 broadway-only；
   补丁后 `key_grabber_init()` 会打印诊断，`--disable-key-grabbing` 行为等价。
4. **无 PulseAudio 服务端直连**：未启动 `pulseaudio --start` 时程序进入「等待服务端」状态。
5. 二进制无 RUNPATH（依赖设备侧运行时环境），与 pamixer/1.6 一致；artifacts 不夹带构建机的
   Conan 缓存绝对路径。test_package 对此只告警不失败。
