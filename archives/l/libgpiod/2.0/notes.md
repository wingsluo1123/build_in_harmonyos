# libgpiod 2.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-10
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://mirrors.edge.kernel.org/pub/software/libs/libgpiod/libgpiod-2.0.tar.gz
2. 应用 4 个补丁 (config.guess, config.sub, configure umask, program_invocation_name compat)
3. configure --prefix=$DEFAULT_PREFIX --enable-tools --enable-bindings-cxx
4. make -j2
5. make install DESTDIR=$TEST_PREFIX
6. make check (通过)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | E007 | 添加 HarmonyOS 检测分支到 config.guess |
| 2 | config.sub 不支持 ohos 目标 | E007 | 添加 ohos-linux 和 linux-ohos 到 config.sub |
| 3 | configure 临时文件权限错误 | E011 | umask 077 → 022 |
| 4 | program_invocation_name 未定义 | musl libc 缺少 glibc 扩展 | 在 tools-common.c 添加 __OHOS__ 兼容实现 |

## 源码修改

- autostuff/config.guess: 添加 HarmonyOS 平台检测
- autostuff/config.sub: 添加 ohos 目标支持
- configure: 修复 umask 077 → 022
- tools/tools-common.c: 添加 program_invocation_name musl 兼容代码

## 验证结果

- Conan verify: G1-G4 PASS
- W3 本地 CI 模拟: PASS
- 测试: gpiod_api_version(), line_settings, is_gpiochip_device, chip_open 均通过

## 交付物

- libgpiod.so.3.0.0 + libgpiod.a
- libgpiodcxx.so.2.0.0 + libgpiodcxx.a
- 工具: gpiodetect, gpioget, gpioinfo, gpiomon, gpionotify, gpioset
- 头文件: gpiod.h, gpiod.hpp, gpiodcxx/
- pkgconfig: libgpiod.pc, libgpiodcxx.pc

## 结束记录
- **最终状态**: built (conan verify PASS, W3 CI PASS)
- **编译结束**: 2026-08-10
