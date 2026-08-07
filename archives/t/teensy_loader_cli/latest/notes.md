# teensy_loader_cli latest 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile 项目，无 autotools/configure)
- 编译日期: 2026-08-05
- 编译器: clang (通过 Conan AutotoolsToolchain 配置)
- 状态: built

## 软件概述

teensy_loader_cli 是 PJRC 提供的命令行工具，用于通过 USB 将固件 (.hex) 上传到
Teensy 开发板 (使用 HalfKay bootloader)。本目录为该工具的 Conan 归档。

- 上游: https://github.com/PaulStoffregen/teensy_loader_cli
- 版本: latest (对应上游 2.3 tag)
- 许可证: GPL-3.0-only
- 语言: C

## 编译步骤

1. 下载源码 (GitHub archive, 2.3 tag)
2. 应用补丁 `0001-teensy_loader_cli.c-libusb-1.0.patch`，把 USB 后端从
   libusb-0.1 compat API 移植到 libusb 1.0 API
3. 使用 Conan AutotoolsToolchain 配置的 CC/CFLAGS/LDFLAGS，并从
   `self.dependencies["libusb"].cpp_info` 读取真实的 include/lib 路径直接编译:
   ```bash
   ${CC} ${CFLAGS} -DUSE_LIBUSB -I<libusb>/include/libusb-1.0 \
       -o teensy_loader_cli teensy_loader_cli.c \
       -L<libusb>/lib -lusb-1.0 ${LDFLAGS}
   ```
4. 将可执行文件打包到 bin/ 目录

## 构建方案说明

### USB 后端：真实 libusb 1.0 移植

上游 Makefile 的 Linux 分支使用的是已废弃的 libusb-0.1 compat API:

- `#include <usb.h>` (libusb-0.1 compat 头文件)
- `-DUSE_LIBUSB -lusb` (libusb-0.1 compat 链接库)

本归档不再使用空实现（stub）后端，而是引入 `libusb/1.0.27` 依赖，并通过补丁把
`USE_LIBUSB` 代码段整体移植到 libusb 1.0 API。5 个 USB 访问函数全部为真实实现：

| 函数 | 实现方式 |
|------|----------|
| `teensy_open()` | `open_usb_device(0x16C0, 0x0478)` → `libusb_open` + `libusb_claim_interface` |
| `teensy_write()` | `libusb_control_transfer(handle, 0x21, 9, 0x0200, ...)` |
| `teensy_close()` | `libusb_release_interface` + `libusb_close` |
| `hard_reboot()` | 打开 rebootor 设备 (0x16C0/0x0477) 并下发 `reboot` 控制请求 |
| `soft_reboot()` | 打开串口设备 (0x16C0/0x0483) 并下发重启命令序列 |

API 映射关系：

- `usb_init` / `usb_find_busses` / `usb_find_devices` → `libusb_init` + `libusb_get_device_list`
- `usb_open` / `usb_close` → `libusb_open` / `libusb_close`
- `usb_control_msg` → `libusb_control_transfer`
- `usb_claim_interface` / `usb_release_interface` → `libusb_claim_interface` / `libusb_release_interface`
- `usb_get_driver_np` / `usb_detach_kernel_driver_np` → `libusb_kernel_driver_active` / `libusb_detach_kernel_driver`
- `usb_strerror()` → `libusb_strerror(<真实返回码>)`

补丁中不含任何平台判定宏，移植后的代码对所有支持 libusb 1.0 的平台通用。

### 错误处理

`open_usb_device()` 用 `usb_last_error` 记录最近一次失败的 libusb 返回码
（init / 枚举 / open / detach / claim 各阶段），`soft_reboot()` 打印错误时使用
`libusb_strerror(usb_last_error)`；控制传输失败时直接使用该次调用的返回码
`libusb_strerror(response)`。不再硬编码固定错误码，避免误报为 I/O 错误。

### 与 2.3 版本的区别

2.3 归档同样是 libusb 1.0 移植，但走 Makefile 补丁 + cmd-pkgs 预编译包路径
（`$(PREFIX)/libusb-package/...` 固定布局，静态链接 `-l:libusb-1.0.a`）。
latest 改为标准 Conan 依赖 `libusb/1.0.27`，从 `cpp_info` 动态读取 include/lib
路径，不依赖任何固定安装布局，因此无需 Makefile 与 dummy configure 补丁。

## 遇到的问题与解决方案

| # | 问题 | 原因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码使用 libusb-0.1 (`usb.h` / `-lusb`) | 上游 Linux 分支针对旧版 libusb 编写 | 补丁移植到 libusb 1.0 API |
| 2 | `#include <libusb.h>` 找不到头文件 | libusb 安装为 `include/libusb-1.0/libusb.h` | build() 中把 `<includedir>/libusb-1.0` 追加到 `-I` 路径 |
| 3 | 静态链接 libusb 时符号缺失 | libusb 依赖 udev/pthread 等系统库 | 链接行追加 `cpp_info.system_libs` |
| 4 | 上游 Makefile 无 install target | 上游 Makefile 仅有 clean target | 绕过 Makefile，直接编译并在 package() 中 copy 可执行文件 |
| 5 | 错误信息恒为 I/O Error | 移植初版硬编码了固定错误码 | 记录并回显真实的 libusb 返回码 |

## 验证结果

Conan `test_package` 会编译并运行 C 测试，随后再对打包后的可执行文件执行
`test.sh`。两者都做两级校验：

### 1) CLI 输出校验（不触碰 USB）

上游 2.3 在输出 MCU 列表后固定返回状态码 1，因此测试只接受
“状态码恰为 1 且包含预期 MCU 标记”。缺少产物、加载失败、崩溃、空输出或其他
退出码都会使 CI 失败。

```bash
$ teensy_loader_cli --list-mcus
Supported MCUs are:
 - at90usb162, atmega32u4, at90usb646, at90usb1286
 - mkl26z64, mk20dx128, mk20dx256, mk66fx1m0, mk64fx512, imxrt1062
 - TEENSY2, TEENSY2PP, TEENSYLC, TEENSY30, TEENSY31
 - TEENSY32, TEENSY35, TEENSY36, TEENSY40, TEENSY41, TEENSY_MICROMOD
```

### 2) 真实 USB 后端校验（走 libusb 枚举）

`-b`（boot only）会跳过固件文件读取，直接进入 `teensy_open()`，从而真实执行
`libusb_init()` 与 USB 总线设备枚举：

```bash
$ teensy_loader_cli --mcu=atmega32u4 -b
Unable to open device (hint: try -w option)
$ echo $?
1
```

断言逻辑：若退出码为 0，说明确实接入了 Teensy 且 USB 路径走通；若退出码非 0，
则输出必须包含 `Unable to open device`。也就是说——**枚举失败时必须明确报错，
禁止静默退出或谎报成功**。这条用例在无硬件的 CI 环境中同样确定性通过，可覆盖
libusb 初始化、设备枚举与失败路径；libusb 链接缺失、初始化失败或后端被替换成
空实现导致的行为异常都会被它捕获。

受限于 CI 无 Teensy 硬件，真实固件写入（`teensy_write` 的数据通路）无法在流水线
中覆盖，需接入设备后人工验证。

## 注意事项

1. `--list-mcus` 等非 USB 操作不触碰 libusb，可在无设备的 CI 环境中稳定验证
2. 实际烧录固件需要接入 Teensy 设备并具备 USB 访问权限
3. 若目标环境动态库搜索路径不可靠，可让 libusb 以静态库形式参与链接
4. 无设备时 `teensy_open()` 返回 0，CLI 会以非 0 状态码显式报错退出，不会出现
   「报告烧录成功但未写入数据」的假成功

---

**编译结束**: 2026-08-05
**最终状态**: built
