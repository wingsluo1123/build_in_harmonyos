# libretro

libretro 是 RetroArch 模拟器前端的事实标准 ABI 规范。本包对应 **libretro/yabause**（世嘉土星模拟器 libretro 核），pin 到 master 提交 `8926b0c6c347`（2026-05-30）。

## 功能概述

- 以 `.so` 插件形式发布（`yabause_libretro.so`），由 libretro 前端（RetroArch 等）按确切文件名 dlopen 加载
- 提供 `libretro.h` 头文件（libretro ABI 接口声明）
- 消费面 = `libretro.h` + 插件 `.so` 的 `retro_*` ABI
- 纯 Makefile 构建（yabause/src/libretro/Makefile），无 configure/cmake

## OHOS 适配要点

- 所有依赖自包含：zlib 1.2.11 / LZMA / FLAC 1.3.3 / libchdr / libretro-common 全部 vendored in-tree
- 无 conan registry 依赖，仅系统 pthreads
- 编译：`make CC=clang CXX=clang++ -j1`（-j1 规避 HMFS 并发 EACCES）
- 链接：`-Wl,--version-script=link.T`（API 导出表）
- 构建时输出重定向到文件再 cat 回（规避 FUSE 管道 EACCES 导致工具链静默退出）
- 上游测试：vendored libretro-common 含 5 个 libcheck 单元测试（127 项 checks），在沙箱需设置 `TEMP=<可写目录>` 重定向 libcheck 内部通信临时文件（/tmp 只读 + P_tmpdir 优先级问题）

## 依赖关系

- **编译依赖**: 无 registry 依赖
- **运行依赖**: 无（前端通过 dlopen 加载）

## 参考资料

- 上游: https://github.com/libretro/yabause
- libretro 规范: https://docs.libretro.com
- 版本: 20260530.083400.g8926b0c6c347
