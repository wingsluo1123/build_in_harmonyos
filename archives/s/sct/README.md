# sct

> X11 屏幕色温调节命令行工具（通过 XRandR gamma 实现）

## 简介

sct 是一个极简的 X11 命令行工具，用 XRandR 的 CRTC gamma 表把屏幕色温设置为
指定的开尔文值（1000K–10000K，默认 6500K），常用于夜间护眼/减少蓝光。
本项目为 Ted Unangst 的 sct 的 FreeBSD 移植版（0mp/sct），源码为公有领域
（Unlicense）。

## 功能概述

- `sct [temperature]`：设置屏幕色温，例如 `sct 3000`
- 无参数时恢复 6500K；超出 1000–10000K 的参数回落到 6500K
- 通过 XRandR 对每个 CRTC 写入 gamma 表，无需额外配置文件

## OHOS 适配要点

- X11 / XRandR 库来自 ohpcd 制品仓（libxrandr/1.5.5.1 传递 libx11/6.4.0、
  libxrender、libxext、xorgproto），构建时不使用 `/usr/local` 宿主机路径。
- 上游 Makefile 通过 `LDFLAGS += -lX11 -lXrandr` 追加链接参数；配方必须用
  环境变量（而非 make 命令行变量）传入 CFLAGS/LDFLAGS，否则追加会被覆盖
  （见知识草稿 DRAFT-sct-1.0.0-make-commandline-var-suppresses-append）。
- HarmonyOS PC 默认不运行 X server：无 DISPLAY 时工具按上游契约返回 1 并打印
  `Failed to open X display`；实际调色需要可用的 X11 + XRandR 环境。
- 上游 `sct.c` 先打开 display 再解析 argv，因此参数范围钳制逻辑需要真实
  X server 才能覆盖（test_package 在检测到 X server 时执行该路径）。

## 依赖关系

- 编译依赖：libxrandr/1.5.5.1（及其传递依赖 libx11/6.4.0、libxrender/0.9.12、
  libxext/6.4.0、xorgproto/2025.1），均从 ohpcd 制品仓获取
- 运行依赖：目标系统的 X11 库（libX11.so.6、libXrandr.so.2）与 X server

## 参考资料

- 上游仓库：https://github.com/0mp/sct
- 原始 sct（Ted Unangst）：http://www.tedunangst.com/flak/post/sct-set-color-temperature
- XRandR 协议：https://www.x.org/releases/X11R7.7/doc/randrproto/randrproto.txt
