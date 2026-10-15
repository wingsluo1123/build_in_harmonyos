# kooha-mp4 - HarmonyOS PC 适配

## 软件简介

Kooha 是 GNOME 生态的极简录屏应用（"Elegantly record your screen"），以 GTK4 +
libadwaita 构建界面，通过 xdg-desktop-portal 的 ScreenCast 接口获取屏幕流，
GStreamer 管线编码输出 WebM / MP4 / Matroska / GIF（mp4 为其核心输出格式，
任务名 kooha-mp4 即指此应用本体）。支持麦克风/桌面音频混合录制、录制延时、
区域选择预览。

- 上游：https://github.com/Seadve/Kooha
- 许可证：GPL-3.0-or-later
- 技术栈：Rust（gtk4-rs 0.7 / libadwaita-rs 0.5 / gstreamer-rs 0.21）+ Meson

## 适配状态

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.2.4 | built | 编译通过 + 上游单测纯逻辑用例全绿；运行需 Broadway 显示会话（见 2.2.4/notes.md） |

## 构建

```bash
conan create . kooha-mp4/2.2.4 \
  -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 \
  --build=missing -c tools.build:jobs=2
```

## 平台适配要点

- gtk4/4.22.4 制品为 Broadway-only 后端：gdk4-wayland/gdk4-x11 裁除，
  portal 窗口标识退化为空串（合法）；预览 sink 由 gtk4paintablesink 降级
  fakesink + MemoryTexture 占位（patch 0001）
- Rust 工具链来自 rust-toolchain/1.97.1（tool_requires，below/0.11.0 先例），
  配方内签名后执行
- 单一 GLib 运行时：gstreamer 静态档案符号全部由 glib/2.84.0.1.1 动态库
  满足（llvm-nm 验证），glib2 pkg-config 刻意排除出构建环境
- gettext 链接期缺口由 identity shim（libintl.a，C locale 语义）填补
