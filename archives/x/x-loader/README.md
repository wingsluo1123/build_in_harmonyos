# x-loader

x-loader (the `MLO` image) is the first-stage bootloader for Texas Instruments
OMAP2/3/4 boards, including the BeagleBoard (OMAP3530, Cortex-A8). It is loaded
by the SoC ROM and in turn loads the second-stage bootloader (e.g. U-Boot) from
NAND / MMC.

## 包内容

| 路径 | 说明 |
|------|------|
| `bin/signGP` | 主机构建工具（HarmonyOS PC aarch64 原生），为裸镜像加上 TI 签名头（镜像大小 + 加载地址） |
| `share/x-loader/MLO` | 可烧写的签名镜像（BeagleBoard / OMAP3530 板级配置） |
| `share/x-loader/x-load.bin.ift` | 与 `MLO` 内容一致的签名镜像 |
| `share/x-loader/x-load.bin` | `objcopy -O binary` 生成的裸镜像 |
| `share/x-loader/x-load.elf` | 带符号/调试信息的 ELF（ARM, entry `0x40200800`） |
| `share/x-loader/System.map` / `x-load.map` | 符号表与链接映射 |

## 适配说明

x-loader 是**裸机 ARM 固件**，上游 Makefile 默认使用 `arm-none-linux-gnueabi-`
GNU 工具链交叉编译。HarmonyOS PC 的 clang 15 是完整交叉编译器（已注册 ARM
后端）并自带 LLVM binutils，因此本配方用

```sh
make omap3530beagle_config
CFLAGS= HOSTCFLAGS= make -j1 CROSS_COMPILE= \
  CC="clang --target=arm-none-eabi" \
  LD=ld.lld AR=llvm-ar NM=llvm-nm STRIP=llvm-strip \
  OBJCOPY=llvm-objcopy OBJDUMP=llvm-objdump HOSTCC=clang \
  AFLAGS_DEBUG= PLATFORM_RELFLAGS= PLATFORM_LIBS= OBJCFLAGS= all
```

原样复用上游 Makefile，仅去掉 clang/LLVM 不支持的 GNU 专用参数。
`signGP` 则用宿主 clang 原生编译（aarch64 + musl），可在鸿蒙 PC 上直接生成
签名镜像。

## 常用命令

```sh
signGP --version
signGP --help
signGP x-load.bin 0x40200800      # 生成 x-load.bin.ift
```

## 上游资源

- 上游仓库: https://github.com/joelagnel/x-loader
- 许可证: GPL-2.0-or-later

## 已知限制

- 仅适配 `omap3530beagle`（BeagleBoard / OMAP3530）板级配置；其他板子需要修改
  `BOARD` 并重新构建。
- 生成的 `MLO` 是给 OMAP 目标板烧写的固件，不在 HarmonyOS 上运行；可在
  HarmonyOS 上运行的是主机构建工具 `signGP`。
- 上游无自动化测试套件，验证依赖构建本身与 `signGP` 往返一致性（见
  `test_package/`）。
