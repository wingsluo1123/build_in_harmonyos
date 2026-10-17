# wayland-utils

**wayland-info** — Wayland 合成器信息查询工具（weston-info 的继任者）。

## Description
连接 Wayland 合成器并打印其通告的协议 globals：接口名/版本/请求计数、
wl_shm 格式（fourcc）、输出/座位信息；启用 DRM 时额外打印 format
modifier 与 lease 信息。wayland 生态的标准诊断工具。

## Homepage
https://gitlab.freedesktop.org/wayland/wayland-utils

## License
MIT

## Build System
Meson

## Dependencies
- wayland/1.24.0
- wayland-protocols/1.48
- libdrm/2.4.133
