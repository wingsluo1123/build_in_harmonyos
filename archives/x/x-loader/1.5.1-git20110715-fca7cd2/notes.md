# x-loader 1.5.1-git20110715-fca7cd2 适配笔记

## 编译环境
- 构建系统: makefile（上游自带 Makefile + mkconfig）
- 编译日期: 2026-10-15
- 编译器: HarmonyOS 6.0 PC 环境 clang 15（`--target=arm-none-eabi` 交叉编译固件；宿主侧 signGP 原生编译）
- 目标板: `omap3530beagle`（BeagleBoard / OMAP3530，Cortex-A8）
- 状态: built

## 概述

x-loader（`MLO`）是 TI OMAP2/3/4 的一级引导加载器，属于**裸机 ARM 固件**：
上游 Makefile 默认用 `arm-none-linux-gnueabi-` GNU 工具链交叉编译，同时用宿主
`gcc` 编译 `scripts/signGP.c` —— 一个给裸镜像加上 TI 签名头（镜像大小 + 加载
地址）的主机工具。

本适配把同一份上游 Makefile 交给 HarmonyOS PC 的 clang/LLVM：clang 15 是完整
交叉编译器（ARM 后端已注册）并自带 LLVM binutils，因此固件用
`--target=arm-none-eabi` 生成，`signGP` 则用宿主 clang 原生编译为
aarch64 + musl 可执行文件，可在鸿蒙 PC 上直接产出签名镜像。

## 编译步骤

```bash
export L=/data/service/hnp/bin
export CROSS_TC='CROSS_COMPILE= CC=clang --target=arm-none-eabi \
  LD=ld.lld AR=llvm-ar NM=llvm-nm STRIP=llvm-strip \
  OBJCOPY=llvm-objcopy OBJDUMP=llvm-objdump HOSTCC=clang'

# 1) 板级配置（mkconfig 生成 include/config.mk 与 include/asm/arch 软链接）
make omap3530beagle_config

# 2) 构建（原样复用上游 Makefile，仅覆盖工具与 GNU 专用参数）
CFLAGS= HOSTCFLAGS= make -j1 CROSS_COMPILE= \
  CC="$L/clang --target=arm-none-eabi" \
  LD="$L/ld.lld" AR="$L/llvm-ar" NM="$L/llvm-nm" STRIP="$L/llvm-strip" \
  OBJCOPY="$L/llvm-objcopy" OBJDUMP="$L/llvm-objdump" HOSTCC="$L/clang" \
  AFLAGS_DEBUG= PLATFORM_RELFLAGS= PLATFORM_LIBS= OBJCFLAGS= all
```

产物：`x-load`（ELF32 ARM）、`x-load.bin`（objcopy -O binary）、
`x-load.bin.ift` = `MLO`（signGP 加签名头）、`System.map`、`x-load.map`、
`signGP`（宿主工具）。

被去掉的 GNU 专用参数及原因：

| 参数 | 原因 |
|------|------|
| `AFLAGS_DEBUG=-Wa,-gstabs` | LLVM 集成汇编器不支持 `-gstabs` |
| `OBJCFLAGS=--gap-fill=0xff` | llvm-objcopy 无 `--gap-fill`；链接脚本段连续，无需填充 |
| `PLATFORM_RELFLAGS`（含 `-ffixed-r8`） | clang 针对 ARM 不支持 `-ffixed-r8`（只认 r9） |
| `PLATFORM_LIBS`（`-lgcc`） | clang 裸机目标没有 libgcc；EABI 除法入口由补丁 0001 提供 |
| `CFLAGS`/`HOSTCFLAGS` 清空 | 上游 Makefile 用 `CFLAGS +=`，调用方泄漏的 CFLAGS 会污染每一行编译命令 |

## 上游测试入口核验（R51）

上游**没有自动化测试套件**：`git ls-files` 中不存在 `tests/`、`test/` 目录，
Makefile 也没有 `check` / `test` / `make check` 目标（只有 `<board>_config`、
`all`/`ift`、`oneboot`、`clean`、`clobber`、`mrproper` 等构建目标）。

实际可执行的验证入口（均已实跑）：

| 入口 | 命令 | 结果 |
|------|------|------|
| 构建 | `make omap3530beagle_config && make` | 通过（39 个上游告警，0 error） |
| 签名往返 | `signGP x-load.bin 0x40200800` | `x-load.bin.ift` 与 `MLO` 逐字节一致 |
| `oneboot` | `make ... oneboot` | **不可直接使用**：`scripts/mkoneboot.sh` 上游权限为 0644（无执行位），且需与本配方相同的交叉工具覆盖；用 `sh scripts/mkoneboot.sh` 手动执行可产出 24364 字节的 `x-load-signed.ift`（512 字节零填充 + 签名镜像） |

`oneboot` 的权限问题是上游缺陷（`make oneboot` 在原 GNU 工具链下同样会
`Permission denied`），本适配不修改。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `clang: unknown argument '-ffixed-r8'` | clang 的 ARM 后端只允许 `-ffixed-r9` 等，不接受 r8 | 命令行覆盖 `PLATFORM_RELFLAGS=`，去掉该参数（上游用它保留 r8，本板代码未依赖该寄存器约定） |
| 2 | `clang: unsupported argument '-gstabs' to option '-Wa,'` | LLVM 集成汇编器不支持 GNU `-gstabs` | 命令行覆盖 `AFLAGS_DEBUG=` |
| 3 | `lib/_udivsi3.S:59: instruction 'movne' can not set flags, but 's' suffix specified` | 上游用 GNU as 的旧写法 `movnes`，clang 只认 `movsne` | 补丁 0001/0002 改为 `movsne` |
| 4 | `lib/_udivsi3.S:67: error: ... (PLT)` | `bl __div0 (PLT)` 的 `(PLT)` 后缀 clang 不支持 | 补丁 0001/0002 改为 `bl __div0` |
| 5 | `ld.lld: undefined symbol: __aeabi_idiv / __aeabi_uidiv` | clang 生成 ARM EABI 除法调用，而上游只提供旧命名 `__udivsi3`/`__umodsi3`；`arm-linux-ohos` 的 compiler-rt builtins 会与 `__udivsi3` 重复定义 | 补丁 0001 在 `_udivsi3.S` 内补出 `__aeabi_uidiv`/`__aeabi_idiv`（后者做符号处理），不引入 libgcc/compiler-rt |
| 6 | `llvm-objcopy: error: unknown argument '--gap-fill=0xff'` | LLVM objcopy 无此 GNU 选项 | 命令行覆盖 `OBJCFLAGS=` |
| 7 | `signGP --version` / `--help` 返回非 0（L2 smoke gate） | 上游 signGP 只认位置参数，长选项被当成文件名 | 补丁 0003 在 `main()` 开头拦截 `--version`/`--help`/`-h` 并 `return 0`（E503 推荐方案） |
| 8 | 编译行出现多余 `-fPIC -O2` | 调用方 shell 导出的 `CFLAGS` 被上游 `CFLAGS +=` 继承 | 构建命令前置 `CFLAGS= HOSTCFLAGS=` 清空环境变量 |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| `patches/0001-lib-_udivsi3.S.patch` | `lib/_udivsi3.S` | `movnes`→`movsne`；去掉 `(PLT)`；新增 `__aeabi_uidiv`/`__aeabi_idiv` ARM EABI 除法入口 |
| `patches/0002-lib-_umodsi3.S.patch` | `lib/_umodsi3.S` | `movnes`→`movsne`；去掉 `(PLT)` |
| `patches/0003-scripts-signGP.c.patch` | `scripts/signGP.c` | `main()` 开头新增 `--version`/`--help`/`-h` 长选项（返回 0，L2 smoke gate / E503） |

补丁均为 clang/LLVM 工具链兼容性修复，与平台宏（`__OHOS__` 等）无关，可无条件应用；
内核为目标板固件，补丁本身不引入任何运行时平台分支。

## 依赖版本

- 无外部依赖（自包含构建）。
- Conan 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`。
- 工具链：clang 15.0.4 + LLVM binutils（`ld.lld` / `llvm-ar` / `llvm-nm` /
  `llvm-strip` / `llvm-objcopy` / `llvm-objdump`）。

## 验证结果

```bash
# 真实构建（conan create，从干净源码拉取 + 打补丁 + 交叉编译 + 宿主工具）
$ conan create archives/x/x-loader/1.5.1-git20110715-fca7cd2 \
      --profile:h=ci/conan/profiles/ohos-aarch64 \
      --profile:b=ci/conan/profiles/ohos-aarch64
# exit code 0

# test_package 通用检查：13 passed, 0 failed
# test_package 鸿蒙特有检查：12 passed, 0 failed
```

- `conan create`：通过（0 error / 39 上游告警），日志 `.ci_logs/x-loader-conan-create.log`。
- 上游测试：无自动化测试套件（见上表，已逐一实测构建 / 签名往返 / oneboot 入口）。
- 产物校验：`MLO` 与 `x-load.bin.ift` 逐字节一致；签名头 size 字段 == `x-load.bin` 大小
  （23844），load address == `0x40200800`；`x-load.elf` 为 ELF32 小端 ARM，入口
  `0x40200800`；`MLO` 载荷首字为 ARM 分支指令 `0xEA000012`（复位向量）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/signGP` | 27136 | 宿主签名工具（aarch64 + musl，鸿蒙 PC 原生可执行） |
| `share/x-loader/MLO` | 23852 | 可烧写签名镜像（BeagleBoard / OMAP3530） |
| `share/x-loader/x-load.bin.ift` | 23852 | 与 `MLO` 内容一致的签名镜像 |
| `share/x-loader/x-load.bin` | 23844 | 裸镜像（`objcopy -O binary`） |
| `share/x-loader/x-load.elf` | 115648 | 带符号/调试信息的 ELF（ARM） |
| `share/x-loader/System.map` | 4944 | 符号表 |
| `share/x-loader/x-load.map` | 30256 | 链接映射 |
| `licenses/README` | 3698 | 上游 GPL 声明（上游未单独提供 COPYING） |

`MLO` sha256 = `0fe098c4fd165208b8633dfdf10fa19262845af8f49a80bf3a8d36cddb3ee292`

## 注意事项

- 仅适配 `omap3530beagle`（BeagleBoard / OMAP3530）。其他板子需改 `BOARD` 并重建；
  `omap4430panda` 走 `cpu/omap4`，其 `config.mk` 另开 `-Werror`，需另行核验。
- 产物 `MLO`/`x-load.bin.ift` 是给 OMAP 目标板烧写的固件，**不在 HarmonyOS 上运行**；
  可在鸿蒙 PC 上运行的是宿主工具 `signGP`。
- `signGP` 打的是 TI 的 image header（大小 + 加载地址），不是安全签名；上板仍需
  TI 的正式签名/烧写流程。
- 上游 `signGP.c` 的 `if (!fclose(f))` 是反向判断，成功时也会打印
  `warning: fclose: No error information`；属上游缺陷，不影响退出码与产物，未修改。
- 构建过程的 39 条告警全部来自上游 2011 年代的代码（隐式声明、无符号/指针比较、
  空循环体等），未修改上游源码。
---

**编译结束**: 2026-10-15 18:57
**最终状态**: built
