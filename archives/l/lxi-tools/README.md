# lxi-tools

lxi-tools 是用于发现和控制 LXI 网络测试仪器的命令行与 GTK4 桌面工具。

## 功能概述

- 通过 VXI-11 或 RAW/TCP 发送 SCPI 命令。
- 发现 LXI 设备、运行 Lua 自动化脚本并执行吞吐基准。
- 提供 GTK4 图形界面及多种仪器截图插件。

## OHOS 适配

- 保留上游默认 GUI，同时交付 `lxi` 与 `lxi-gui`。
- 使用 Conan 提供的 liblxi、Lua、readline 和完整 GTK4 依赖闭包。
- RAW/SCPI 查询按换行或 IEEE 488.2 definite-length block 长度跨读取周期组帧。
- 最终 AArch64 ELF 去除构建路径与 RPATH/RUNPATH 后进行 HarmonyOS 签名。

## 依赖关系

核心依赖为 liblxi、Lua 和 readline；GUI 依赖 GTK4、GLib、libadwaita、GtkSourceView 5、json-glib、Cairo 与 GdkPixbuf。

## 参考资料

- 项目主页：https://lxi-tools.github.io/
- 源码仓库：https://github.com/lxi-tools/lxi-tools
