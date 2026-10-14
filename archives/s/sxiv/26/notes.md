# sxiv 26 适配笔记

## 编译环境

- 构建系统: 裸 Makefile
- 编译器: OHOS profile 中的 `tools.build:compiler_executables.c`
- 目标: HarmonyOS PC / OHOS aarch64
- 状态: 设备端 `conan create --build=missing` 已通过

## 依赖与兼容层

上游 sxiv 26 依赖 Imlib2 的 X11 drawable API。OHPCD 已发布的
`imlib2/1.9.1` 使用 `--without-x` 构建，因此不包含以下符号：

`imlib_context_set_display`、`imlib_context_set_visual`、
`imlib_context_set_colormap`、`imlib_context_set_drawable`、
`imlib_render_image_on_drawable`、
`imlib_render_image_on_drawable_at_size`、
`imlib_render_image_part_on_drawable_at_size`。

本配方没有为 sxiv 附带重新发布 imlib2，而是保留已发布的 Imlib2
图像加载、缩放和颜色修正流程，在 `ohos_x11_render.c` 中用真实
`libX11` 的 `XCreateImage`、`XGetImage`、`XPutImage` 补齐 drawable
操作，并做 RGBA alpha 混合。`ohos_x11_render.h` 通过 `-include`
注入到上游编译单元，避免修改上游源码。

## 构建要点

- `AUTORELOAD=nop`：OHOS 内核不提供 inotify，使用上游自带 nop 后端。
- `objs` 覆盖为 `autoreload_nop.o` 和 `ohos_x11_render.o`，避免默认
  `autoreload_inotify.o` 被链接。
- include/lib 路径从全部 host 依赖的 `cpp_info` 聚合注入。
- 链接集：`-lImlib2 -lX11 -lXft -lfontconfig -lexif -lgif`。
- `install` 目标复用同一套 `AUTORELOAD`、`objs` 变量，避免安装阶段
  回头编译错误的默认目标。

## 测试

上游 sxiv 26 没有 `check`/`test` 目标。`test_package` 编译一个安装后
冒烟测试程序并执行：

1. 检查安装的 `bin/sxiv` 是普通可执行文件。
2. 运行 `sxiv -v`，确认动态链接闭包可加载且版本路径正常退出。

设备端验证任务 `20261013-000644-c81107-sxiv-10958-create-r2` 返回
`conan_create_rc=0`，消费者测试输出 `sxiv installed executable check`
`passed` 和 `sxiv 26`。

OHOS 消费者测试会先把依赖共享库汇总到临时目录并重新 self-sign，再用
该目录作为 `LD_LIBRARY_PATH` 运行；这避免预构建依赖的 `.codesign` 在
设备侧被拒绝，同时不改动制品仓中的库。

## 已知边界

`sxiv` 是 X11 GUI 程序，CI 无 X display，因此不启动窗口；测试只覆盖
安装、加载、版本输出和无显示启动路径。真正的图像渲染需要带 X server
的设备或用户会话，后续真机验证时可补充窗口级测试。
