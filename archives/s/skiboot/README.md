# skiboot — OpenPOWER OPAL 固件与用户态工具

skiboot 是 OpenPOWER（IBM POWER8/POWER9/POWER10）平台的 OPAL 固件实现，负责
开机引导、运行时服务以及 PNOR 闪存、GARD、XSCOM 等硬件管理。

- 上游仓库：<https://github.com/open-power/skiboot>
- 许可证：Apache-2.0 OR GPL-2.0-or-later

## 功能概述

本包安装的是 skiboot 的可移植用户态工具（与 Debian/Raspbian 在非 ppc64 架构上
打包的范围一致）：

| 工具 | 功能 |
|------|------|
| `pflash` | 读写 PNOR/闪存镜像，查看与修改 FFS 分区表 |
| `opal-gard` | 读取、创建、清除 GARD（Guard）硬件隔离记录 |
| `ffspart` | 生成 FFS/PNOR 镜像（分区布局 → 镜像文件） |
| `getscom` / `putscom` | 读写 POWER 芯片 SCOM 寄存器 |
| `getsram` | 读取 SRAM |

> 固件本体（`skiboot.lid`/`skiboot.elf`）面向 ppc64（`-mcpu=power8`、PowerPC
> 汇编与 `asm/opal-prd.h` UAPI），不属于 aarch64/OHOS 适配范围；
> `external/opal-prd` 同样依赖 PowerPC UAPI，按 Debian 的做法在非 ppc64 上不构建。

## OHOS 适配

- `external/common/get_arch.sh` 增加 `__aarch64__` 识别，使 `pflash`/`ffspart`
  选择 ARM 闪存后端（`ast_ahb_readl`）而不是 `ARCH_UNKNOWN` 桩。
- `ccan/endian/endian.h` 对 musl `alltypes.h` 已定义的字节序宏加保护，
  避免 `-Werror` 下的宏重定义错误。
- `external/gard/rules.mk` 先探测 `-Wno-stringop-truncation` 再使用
  （clang 无此 GCC 警告）。
- `libflash/file.c` 的 readlink 缓冲改用 `PATH_MAX`（OHOS procfs 的 `st_size` 固定 64，
  按它分配会截断长路径）。
- 部分 CI worker 的沙箱会拒绝执行 pflash/opal-gard 等硬件工具（EPERM）；此时上游
  测试如实标记 `skipped_sandbox`，消费者测试降级为静态 ELF/符号校验。
- `make_version.sh` / `test/run.sh` 解释器改为 `/usr/bin/env bash`（OHOS 无 `/bin/bash`）。
- 上游测试脚本的 GNU 长选项（`stat --printf`、`cmp --bytes/--ignore-initial`）
  改为 POSIX/toybox 可用的 `stat -c`、`cmp -n` 形式；并修正 ffspart
  第 18 例 `|| echo && exit 0` 的优先级问题，使其在 PATH 中存在 pflash 时真正执行。

## 依赖关系

- 编译：无第三方 Conan 依赖，仅需 OHOS clang 与 make。
- 运行：无动态库依赖（musl libc），工具面向 POWER 硬件操作，在非 POWER
  机器上只能处理镜像文件（如 `pflash -F`、`ffspart`、`opal-gard -f`）。

## 测试

- 上游可运行用例共 84 例，全部在 OHOS aarch64 主机上真实执行：
  `external/{pflash,gard,ffspart}/test` 37 例 + `make check` 主宿机单测 47 例
  （ccan 15、core 15、libc 4、libflash 4、libstb 1、secvar 7、hw/ipmi 1）。
  其余 ppc64 专属或依赖缺失的用例在 notes.md 中逐组列明。
- `test_package/test_ohos.py` 增加鸿蒙消费者断言：AArch64/musl ELF、
  ARM 闪存后端选择、符号/版本字符串；可执行时追加 ffspart→pflash 镜像往返与
  分区擦写（38 项），CI 沙箱禁止执行时降级为 26 项静态断言。

## 参考资料

- <https://github.com/open-power/skiboot>
- <https://github.com/open-power/skiboot/tree/master/external>
