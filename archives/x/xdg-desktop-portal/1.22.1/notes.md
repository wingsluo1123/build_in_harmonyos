# xdg-desktop-portal 1.22.1 — OHOS PC 适配笔记

## 软件定位（先纠正两个常见误判）

1. **不链接 flatpak**。xdg-desktop-portal 是 D-Bus portal 服务框架（daemon），
   flatpak 只是它的使用方之一。上游 meson.build 中 flatpak 仅作为可选的
   接口文件来源（`-Dflatpak-interfaces=disabled` 即完全无关）。
2. **不产出 libportal**。libportal 是独立项目（本仓已在档 libportal/0.10.0），
   提供 C 便捷 API 库；xdg-desktop-portal 交付的是守护进程+接口 XML+配置。

## 交付物

| 路径 | 说明 |
|---|---|
| `libexec/xdg-desktop-portal` | portal 守护进程（核心交付） |
| `libexec/xdg-desktop-portal-validate-icon` | 图标校验助手（依赖 gdk-pixbuf，保留） |
| `libexec/xdg-permission-store` | 权限存储守护进程（gvdb+glib，无 fuse3） |
| `share/dbus-1/interfaces/*.xml` | portal D-Bus 接口 XML（60+，消费者编译时用） |
| `share/dbus-1/services/*.service` | D-Bus 激活文件 |
| `lib/systemd/user/*.service` | systemd user 单元（数据文件，OHOS 无 systemd 但作为标准布局交付） |
| `lib/pkgconfig/xdg-desktop-portal.pc` | dataonly pc（`interfaces_dir` 变量指向接口 XML） |

## 裁剪决策（A 方案，主 agent 已裁决）

上游 1.22.1 三个**硬依赖**均不在 OHOS 制品仓（conan search 实测 0 命中）：

| 依赖 | 上游用途 | 处置 |
|---|---|---|
| fuse3 >= 3.10.0 | document portal 的 FUSE 挂载后端 | feature 选项化 + disabled |
| libpipewire-0.3 >= 0.2.90 | camera / screen-cast / remote-desktop / clipboard portal 的视频源 | feature 选项化 + disabled |
| gstreamer-pbutils-1.0 | validate-sound 声音校验助手 | feature 选项化 + disabled |

**核验结论**：gst-plugins-base 1.28.3 配方只包装 gstreamer core 的 5 个 pc
（gstreamer/base/controller/net/check + glib2 系 + orc/ogg/vorbis/alsa/libdrm/iso-codes），
**不生成 gstreamer-pbutils-1.0.pc**，故 pbutils 并入裁剪面（主 agent 裁决细节 #2）。

**模式对齐**：上游 meson.build 对 geoclue/gudev/systemd 已有
`dependency(..., required: get_option(...))` + `config_h.set10('HAVE_X', ...)` 的
可选模式，本补丁完全复制该模式（fuse3/pipewire 新增 HAVE_FUSE3/HAVE_PIPEWIRE
宏，sound-validation 直接用 found() 分支）。C 侧守卫：
- `src/xdp-context.c`：`#if HAVE_PIPEWIRE` 守卫 camera/clipboard/remote-desktop/
  screen-cast 的 include 与 init 调用（clipboard 依赖 remote-desktop 会话，
  归入 pipewire 组）
- `src/meson.build`：对应 .c 文件移入 `if have_pipewire` 块；validate-sound
  移入 `if gst_pbutils_dep.found()` 块
- `document-portal/meson.build`：`if not have_fuse3` 时 `subdir_done()`——
  关键洞察是 xdg-permission-store 在文件前部且不依赖 fuse3，只跳过后面的
  FUSE 挂载后端（document-portal.c/file-transfer.c/document-store.c/
  document-portal-fuse.c + Documents.service），permission-store 的
  gdbus-codegen 与 PermissionStore.service 保留

**input-capture 保留原因**：不引用 pipewire 头（只调 remote-desktop 的
clipboard 会话函数……实际核验：input-capture.c 无 pipewire/remote-desktop/
screen_cast 符号引用，只有自身 clipboard_enabled 字段处理），保留编译。

## 其余禁用项（标准 OHOS 桌面生态缺件）

- `-Dgeoclue=disabled` / `-Dgudev=disabled` / `-Dsystemd=disabled`：无对应守护进程/udev/libsystemd
- `-Dflatpak-interfaces=disabled`：无 flatpak 开发文件
- `-Dtests=disabled`：pytest+dbusmock+umockdev+D-Bus session 均不可得
- `-Dman-pages=disabled` / `-Ddocumentation=disabled`：无 rst2man/sphinx
- `-Dsandboxed-image-validation=disabled` / `-Dsandboxed-sound-validation=disabled`：无 bwrap（OHOS 无 bubblewrap 机制）

## glib 构建期工具链（CI 可复现关键）

上游重度使用 meson gnome 模块：gdbus_codegen×5 + mkenums_simple +
compile_resources + i18n.gettext。meson 的 `ModuleState.find_tool` 查找顺序：
program_from_overrides → machine file → **pkg-config 变量**（gio-2.0.pc 的
gdbus_codegen/glib_compile_resources、glib-2.0.pc 的 glib_mkenums）→ PATH。

本机/CI worker 的坑（实测）：
- `/data/service/hnp/bin/glib-mkenums` shebang 是 `#!/usr/bin/perl`，但
  `/usr/bin/perl` 不存在（bad interpreter）
- `/data/service/hnp/bin/glib-compile-resources` 缺 `libffi.so.8`（reloc 报错）
- conan glib 2.84.0 包内三工具完好：gdbus-codegen/glib-mkenums 是
  `#!/usr/bin/env python3` 脚本（用 sys.executable 包装），glib-compile-resources
  是 musl ELF，需 `LD_LIBRARY_PATH=<glib>/lib` + OHOS codesign 才能 exec

→ 配方 `_stage_glib_tool`（evince 48.4 模式）：python 工具生成 `#!/bin/sh
exec python3 <原脚本>` 包装；ELF 工具 patchelf runpath + llvm-objcopy 去
旧 codesign 段 + binary-sign-tool 重签。包装后回写 pc 变量。

## 其他适配点

- **gio-unix-2.0.pc**：glib 配方组件未含此模块，从 gio-2.0.pc 派生（xdg-dbus-proxy 同款）
- **gdk-pixbuf-2.0.pc 别名**：gdk-pixbuf/2.44.6 无 pkg_config_name，
  PkgConfigDeps 只出 gdk-pixbuf.pc，meson 查询 gdk-pixbuf-2.0 需造别名
- **TMPDIR**：HMDFS /tmp 只读，build_folder/.tmp 兜底
- **PKG_CONFIG_PATH**：显式注入 generators 目录（dconf 先例：buildenv 注入对
  meson configure 不可靠）
- **ELF 签名**：安装后的 daemon/helper 用 objcopy+binary-sign-tool 签名
  （accountsservice 模式），CI L2 smoke 才能跑 `--version`
- **pidfd**：上游已带 `#if HAVE_PIDFD_OPEN` 守卫（musl 无 sys/pidfd.h 时走
  syscall 回退），无需处理
- **renameat2/splice**：走 libglnx 的 glnx_renameat2_noreplace（带回退），无需处理

## 上游测试情况

tests/ 为 pytest+dbusmock 套件（28 文件 189 测试函数），需运行中的 D-Bus
session daemon + python-dbus + dbusmock + umockdev，OHOS CI 不可得。
test_package 以交付物断言替代（daemon --version 的 PACKAGE_STRING、pc 的
interfaces_dir 解析、接口 XML 清单、D-Bus service 文件、15 项断言）。

## 版本

- 1.22.1（2026-04-16 上游发布，当前最新 tag；上游要求 meson >= 0.60、glib >= 2.76）
