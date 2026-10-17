# xdg-desktop-portal

桌面集成 portal 服务框架 — D-Bus portal 守护进程 + 接口 XML。

## 简介

xdg-desktop-portal 是 freedesktop 的 portal 服务框架：一个 D-Bus 守护进程
（`xdg-desktop-portal`），为沙箱化应用代理桌面集成请求（文件选择器、打开
URI、截图、设置、通知等），转发给后端实现（如 xdg-desktop-portal-gtk /
xdg-desktop-portal-hyprland）。

**两个常见误判的澄清**：
- 它**不链接 flatpak**（flatpak 只是 portal 的使用方之一，上游 meson 中
  flatpak 仅作可选接口文件来源）
- 它**不产出 libportal**（那是独立项目，本仓已在档 libportal/0.10.0）

## OpenHarmony 编译说明

- 构建系统: Meson（>= 0.60），上游 1.22.1 要求 glib >= 2.76
- 依赖: glib/2.84.0.1、json-glib/1.10.6、gdk-pixbuf/2.44.6
- fuse3/libpipewire/gstreamer-pbutils 三个上游硬依赖不在 OHOS 制品仓，
  经 portability patch 改造为 meson feature 选项后禁用（对齐上游
  geoclue/gudev 可选模式）；三者只服务 OHOS 无桌面会话态的后端
  （FUSE 挂载 / camera+screen-cast+remote-desktop / 声音校验）
- xdg-permission-store 守护进程不依赖 fuse3，保留交付
- glib 构建期工具（gdbus-codegen/glib-mkenums/glib-compile-resources）从
  conan glib 包取用并包装（CI worker 的 hnp 工具有 perl 缺失/libffi 缺失问题）
- gio-unix-2.0.pc 手工派生；gdk-pixbuf-2.0.pc 造别名
- 上游测试套件（pytest+dbusmock，28 文件 189 测试）需 D-Bus session，
  OHOS CI 不可得，以交付物断言替代（daemon --version / pc interfaces_dir /
  接口 XML 清单 / D-Bus service 文件）

## 交付物

libexec/xdg-desktop-portal、libexec/xdg-desktop-portal-validate-icon、
libexec/xdg-permission-store、share/dbus-1/interfaces/*.xml（60+）、
share/dbus-1/services/*.service、lib/systemd/user/*.service、
lib/pkgconfig/xdg-desktop-portal.pc（dataonly，interfaces_dir 变量）。

## 许可证

LGPL-2.0-or-later

## 主页

https://github.com/flatpak/xdg-desktop-portal

## 版本历史

- 1.22.1 (2026-10-06): OHOS PC aarch64 首版适配
