# pnmixer

pnmixer 是**系统托盘里的 ALSA 音量混音器**：托盘图标显示当前音量/静音状态，
左键弹出音量滑块，右键出菜单切换声卡、静音、打开首选项（GTK+3 前端，C/CMake）。
它是 OBmixer 的衍生作品，而 OBmixer 又源自 AbsVolume。

## 功能概述

- 托盘图标（`GtkStatusIcon`）：滚轮直接调音量，中键静音/取消静音
- 弹出窗口：主音量滑块 + 静音按钮，可选显示「音量」弹窗
- 右键菜单：选择声卡（ALSA card）、选择通道、重新加载音频、首选项、关于、退出
- 首选项：默认/自定义音量控制命令、托盘图标主题、通知开关、快捷键
- 全局快捷键（`hotkey.c`/`hotkeys.c`，X11 `XKBlib` 抓键；OHOS 的 GDK 无 X11 后端，
  本适配降级为不可用，见「源码补丁」）
- 可选桌面通知（libnotify，`-DWITH_LIBNOTIFY=ON`；**本适配置 OFF**，见下）

## OHOS 适配要点

- **构建系统是 CMake**（上游 `CMakeLists.txt` + 各子目录），而 skill 的
  `conan-init` 只会生成 autotools 骨架，因此本配方手写为
  `CMakeToolchain` + `PkgConfigDeps`（§12.56 的已知形态）。
- **依赖经 `pkg_check_modules` 声明**（`src/CMakeLists.txt`）：
  `alsa`、`glib-2.0`、`x11`、`gtk+-3.0>=3.12.0`，以及可选的 `libnotify`。
  制品仓里这些配方的 `pkg_config_name` 与上游模块名**逐字一致**
  （alsa-lib→`alsa`、glib→`glib-2.0`、libx11→`x11`、gtk→`gtk+-3.0`、
  libnotify→`libnotify`），因此 `PkgConfigDeps` 产物**不需要别名补丁**。
  其中 `libnotify` 分支本适配关闭（见下）。
- **CMake 侧的 pkg-config 环境要自己铺**：`AutotoolsToolchain` 会自动把
  generators 目录塞进 `PKG_CONFIG_PATH`，`CMakeToolchain` 不会。本配方在
  `generate()/build()` 里把 generators 目录 + 各依赖 `*/pkgconfig` 目录
  显式写进 `PKG_CONFIG_PATH`，否则 `pkg_check_modules(... REQUIRED)` 直接失败。
- **`cmake_minimum_required(VERSION 3.0)` 与平台 CMake 4.1.2 不兼容**：
  CMake 4.x 移除了对 <3.5 的兼容，必须注入
  `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`；并且必须走
  `CMakeToolchain.cache_variables`（写成普通 `variables` 进的是 toolchain
  文件、不参与策略检查）。
- **libnotify 不声明（`WITH_LIBNOTIFY=OFF`）**，两条独立原因（都已实测留证）：

  1. **制品侧签名缺陷**：`libnotify/0.8.3` 的 `lib/libnotify.so.4.0.0` 带着
     `.codesign` 段，但该签名不被 OHOS 加载器接受——`dlopen` 直接
     `Error loading shared library ...: Permission denied`；把**同一份字节**用
     `binary-sign-tool sign -selfSign 1` 重新签名后就能进入依赖解析。任何链接它的
     交付物都在 `main()` 之前就死（实测 `notify_init: symbol not found`）。
  2. **依赖图冲突 + 无法源码重建**：`libnotify/0.8.3.1` 以 `force=True` 钉
     `glib/2.88.0.1`，与全部已发布 gtk3 的 `glib/2.84.0.1` 不可解
     （`ERROR: Version conflict: between glib/2.88.0.1 and glib/2.84.0.1`）；
     覆盖任一侧都会改 `package_id` 而触发 **meson 源码重建**，而本工具链没有 meson
     （实测 `libnotify/0.8.3.1: Error in build() method, line 145
     meson.configure() → ConanException: Error 127 while executing`，上一行是
     `/bin/sh: meson: inaccessible or not found`）。即使改用同代的
     `libnotify/0.8.3` 绕开 glib 冲突（已合入 `lomiri-polkit-agent/0.3.3` 的做法），
     仍会撞上第 1 条。

  关掉这个上游本来就提供的开关后，图的其余部分全部落到已发布二进制
  （`conan graph info` → `{Cache: 25, Skip: 9}`，零缺失、零源码重建），并且交付物
  **真的能启动**（见下）。附带事实：freedesktop 桌面通知还需要 D-Bus 上的通知守护
  进程，OHOS PC 并不提供，所以即便库能加载该功能也不可用。
- **`ENABLE_NLS` 置 OFF**（已在 PR 正文与 notes 中披露）：
  1. 上游 `CMakeLists.txt` 在 `ENABLE_NLS=ON` 时会
     `FIND_PROGRAM(XGETTEXT_EXECUTABLE xgettext)`，找不到就
     `MESSAGE(FATAL_ERROR "xgettext not found")`。干净 CI worker 不保证有
     gettext 工具链（cliquer 的 automake 同款教训：本地有、CI 无 ⇒ 本地假绿）。
  2. `src/support-intl.h` 在 NLS 打开时 `#include <libintl.h>`；OHOS sysroot 的
     `libintl.h` 是空壳、实现属 gettext 制品（知识条目 E660）。
  OFF 时 `#cmakedefine ENABLE_NLS` 不定义，`intl_init()` 不含任何 gettext
  调用，链接也不需要 `-lintl`。仓内 212 份配方同样关闭 NLS。
  代价：**不安装翻译（.mo）**，界面只出英文。
- **OHOS `/tmp` 是只读 erofs 挂载（E002）**：配方把 `TMPDIR`/`TMP`/`TEMP`
  指到 `build_folder` 下的私有目录，避免 cmake/clang 的临时文件失败。
- **签名**：`package()` 用 `binary-sign-tool` 自签名 `bin/pnmixer`，并回读
  `.codesign` 段计数（OHOS 未签名 ELF 不可加载）；先例 = 已合入的
  `pasystray/0.8.2`。
- **上游 tag archive 的 codeload 直链末段无扩展名**
  （`.../tar.gz/refs/tags/v0.7.2`），`conandata.yml` 必须显式给 `filename`，
  否则 conan 按末段猜格式（E276/E483：猜成 zip → BadZipFile）。

## 依赖关系

编译依赖（配方声明）：

| 依赖 | 版本 | 说明 |
|---|---|---|
| gtk | 3.24.43 | GTK+3（`gtk+-3.0`，broadway 后端），传递提供 glib 2.84.0.1 / gdk-pixbuf 2.44.6.1 / pango / cairo / atk |
| glib | 2.84.0.1 | gtk 闭包钉版 |
| gdk-pixbuf | 2.44.6.1 | 托盘图标解码用（`src/ui-tray-icon.c`），gtk 闭包钉版 |
| alsa-lib | 1.2.16.1 | `libasound`，`src/alsa.c` 直接调 ALSA mixer API |
| libx11 | 1.8.13.1 | `x11`，`src/hotkey.c` 用 `XKBlib` |
| libnotify | 未声明 | `WITH_LIBNOTIFY=OFF`，见上文 |

运行期依赖：GTK3/GLib/ALSA/X11 共享库，另有**显示服务**与一个 **ALSA 声卡**。

## 源码补丁（6 个，全部 `portability`，无平台宏）

| 补丁 | 文件 | 说明 |
|---|---|---|
| 0001 | `src/alsa.c` | `exp10()` 是 GNU 扩展：OHOS 的 `<math.h>` 不声明、共享 libm 不导出 → 换成等价的 `pow(10, x)` |
| 0002 | `src/hotkey.c` | Xlib/XKBlib 抓键代码用 `HAVE_GDK_X11` 守卫，缺失时 no-op |
| 0003 | `src/hotkey.h` | 用 `__has_include(<gdk/gdkx.h>)` 编译期探测后端，缺失时退回 `<gdk/gdk.h>` |
| 0004 | `src/hotkeys.c` | 无 X11 后端时编译掉 root-window key filter；启用热键时给一条明确 WARN |
| 0005 | `src/ui-popup-window.c` | 删除未使用的 `<gdk/gdkx.h>` include（该文件无 `gdk_x11_*` 调用） |
| 0006 | `src/ui-prefs-dialog.c` | 同上 |

## 已知限制（本平台）

- **显示服务**：OHOS PC 没有 X11/Wayland 服务，`gtk/3.24.43` 只编 broadway 后端
  （E527），而 `GtkStatusIcon` 依赖 X11 系统托盘协议 ⇒ **真实桌面环境下的托盘本体
  不可用**。但 broadway 后端反过来提供了可测面：gtk 包自带 `bin/broadwayd`，起一个
  私有 display 之后本交付物能**真正启动**——`--version`/`-v` 打印
  `pnmixer version: 0.7.2`（rc=0），`-d` 启动日志显示它从**已安装的** glade 文件
  建好弹出菜单/弹窗、创建托盘图标、装载 5 张**已安装的** pixmap、创建热键子系统、
  挂载音频子系统，最后进入 `---- Running main loop ----`。消费者测试即以此为准
  （24 项断言：15 结构性/链接性/安装面 + 4 CLI + 1 未知选项落穿 + 1 无显示快速失败
  + 2 有显示版本 + 1 真启动）。
- **无音频设备**：容器内 `/dev/snd` 不可访问，ALSA 报
  `cannot find card '0'` / `Can't attach card to mixer`，程序按设计继续运行
  （`No soundcard could be hooked !`）⇒ mixer 的读写行为不可验证，可验证面是
  「确实链接 libasound」+「音频子系统走到该错误路径而不崩」。
- **通知不可用**：见上文 libnotify 两条原因。
- **翻译未安装**：`ENABLE_NLS=OFF`（上游在 ON 时硬要求 `xgettext`，且 OHOS 的
  `libintl.h` 是空壳，E660）⇒ 界面只出英文。

## 参考资料

- 上游源码：<https://github.com/nicklan/pnmixer>
- 上游 README：<https://github.com/nicklan/pnmixer/blob/master/README.md>
- ALSA mixer API：<https://www.alsa-project.org/alsa-doc/alsa-lib/group___mixer.html>
