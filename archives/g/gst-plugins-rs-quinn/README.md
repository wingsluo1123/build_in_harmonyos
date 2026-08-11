# gst-plugins-rs-quinn 0.15.3

GStreamer QUIC 传输插件（quinn-rs），来自 gst-plugins-rs 工作区
（`net/quinn` crate）。

## 插件元素

- `quinnquicsrc` / `quinnquicsink` — 通过 QUIC 收发数据
- `quinnquicmux` / `quinnquicdemux` — QUIC 流/数据报复用与解复用
- `quinnroqmux` / `quinnroqdemux` — RTP over QUIC (ROQ) 复用与解复用
- `quinnsrc` / `quinnsink` — QUIC/WebTransport 连接与会话共享

## 构建

- 构建系统: cargo (Rust)，产物为 cdylib `libgstquinn.so`
- 安装位置: `lib/gstreamer-1.0/`
- 系统依赖: gstreamer 1.28.x + glib 2.x（cmd-pkgs 预编译包）

## 许可

MPL-2.0
