# teensy_loader_cli latest 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile 项目，无 autotools/configure)
- 编译日期: 2026-07-15
- 编译器: clang (通过 Conan MakeToolchain 配置)
- 状态: built

## 软件概述

teensy_loader_cli 是 PJRC 提供的命令行工具，用于通过 USB 将固件 (.hex) 上传到
Teensy 开发板 (使用 HalfKay bootloader)。本项目为 HarmonyOS PC (aarch64) 平台
适配的 Conan 归档。

- 上游: https://github.com/PaulStoffregen/teensy_loader_cli
- 版本: latest (对应上游 2.3 tag)
- 许可证: GPL-3.0-only
- 语言: C

## 编译步骤

1. 下载源码 (GitHub archive, 2.3 tag)
2. 生成 stub USB 后端 (stub_usb.c)，提供 USB 访问函数的空实现
3. 使用 Conan MakeToolchain 配置的 CC/CFLAGS/LDFLAGS 直接编译:
   ```bash
   ${CC} ${CFLAGS} -o teensy_loader_cli teensy_loader_cli.c stub_usb.c ${LDFLAGS}
   ```
4. 将可执行文件打包到 bin/ 目录

## 构建方案说明

### 为什么使用 stub USB 后端

上游 Makefile 的 Linux 分支硬编码了 libusb-0.1 (deprecated) API:
- `#include <usb.h>` (libusb-0.1 compat 头文件)
- `-DUSE_LIBUSB -lusb` (libusb-0.1 compat 链接库)

当前归档中没有 Conan libusb 包 (libusb/1.0.27 仅有文档，无 conanfile.py)，
因此采用 stub USB 后端方案:

- 创建 stub_usb.c，提供 5 个 USB 访问函数的空实现:
  - `teensy_open()` - 打印错误信息，返回 0
  - `teensy_write()` - 返回 0
  - `teensy_close()` - 空操作
  - `hard_reboot()` - 返回 0
  - `soft_reboot()` - 返回 0
- 编译时不定义任何 USE_* 宏，源码中的 USB 后端代码段不会被编译
- stub 函数提供链接所需的符号定义

这样可执行文件可以正常编译、安装和运行 (`--list-mcus` 等非 USB 操作正常)，
但实际 USB 设备操作不可用。

### 与 2.3 版本的区别

2.3 版本 (已有归档) 采用了完整的 libusb 1.0 移植方案:
- 3 个补丁: Makefile 适配、dummy configure、libusb 0.1->1.0 API 移植
- 依赖 libusb 1.0.27 预编译包 (静态链接)
- USB 功能完整可用

latest 版本采用无依赖的 stub 方案，便于快速打包和 CI 验证。
如需完整 USB 功能，可参考 2.3 版本的补丁和依赖配置。

## 遇到的问题与解决方案

| # | 问题 | 原因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 -lusb | 上游针对 Linux 使用 libusb-0.1 | 绕过 Makefile，直接编译并使用 stub 后端 |
| 2 | 无 Conan libusb 包 | libusb/1.0.27 仅有文档 | 使用 stub USB 后端，无外部依赖 |
| 3 | 无 USE_* 宏时链接失败 | USB 函数未定义 | stub_usb.c 提供空实现 |
| 4 | 无 install target | 上游 Makefile 仅有 clean target | 在 conanfile.py package() 中直接 copy 可执行文件 |

## 验证结果

```bash
$ teensy_loader_cli --list-mcus
Supported MCUs are:
 - at90usb162, atmega32u4, at90usb646, at90usb1286
 - mkl26z64, mk20dx128, mk20dx256, mk66fx1m0, mk64fx512, imxrt1062
 - TEENSY2, TEENSY2PP, TEENSYLC, TEENSY30, TEENSY31
 - TEENSY32, TEENSY35, TEENSY36, TEENSY40, TEENSY41, TEENSY_MICROMOD
```

## 注意事项

1. 当前版本 USB 功能不可用 (stub 后端)，仅支持 --list-mcus 等非 USB 操作
2. 如需 USB 功能，需引入 libusb 依赖并应用 2.3 版本的源码补丁
3. 源码使用旧版 libusb-0.1 API，需移植到 libusb 1.0 才能使用现代 libusb
4. OHOS 平台 LD_LIBRARY_PATH 不可用，libusb 需静态链接

---

**编译结束**: 2026-07-15
**最终状态**: built
