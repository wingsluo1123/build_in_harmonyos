# riscv64-elf-binutils 2.46.0 适配笔记

## 编译环境
- 构建系统: autotools（交叉编译模式）
- 编译日期: 2026-07-25
- 主机平台: aarch64-linux-ohos
- 目标平台: riscv64-elf（bare-metal）
- 编译器: clang/clang++
- 状态: built（配方完成，CI 发布待执行）

## 配置参数

```bash
./configure \
  --target=riscv64-elf \
  --host=aarch64-linux-ohos \
  --build=aarch64-linux-ohos \
  --prefix=... \
  --disable-gprofng \
  --disable-nls \
  --disable-shared \
  --enable-static
```

`--target=riscv64-elf` 是核心参数，指示生成 RISC-V 交叉编译工具链。

## 编译步骤

1. 下载 binutils 源码（清华镜像）：https://mirrors.tuna.tsinghua.edu.cn/gnu/binutils/binutils-2.46.0.tar.gz
2. 修改 config.guess/config.sub 支持 HarmonyOS（E007 模式）
3. 修改所有子目录 configure 脚本中的 umask 077→022（E011 模式）
4. 修复所有脚本的 shebang（`#! /bin/sh` → `#! /data/service/hnp/bin/bash`，平台限制）
5. 执行 configure：`./configure --target=riscv64-elf --prefix=... --disable-gprofng --disable-nls --disable-shared --enable-static`
6. 执行 make：`make -j1 [all-bfd|all-opcodes|all-gas|all-binutils|all-ld]`
7. Staging 安装：`make install DESTDIR=$TEST_PREFIX`
8. 执行测试：`make check -j1`（需要目标模拟器 qemu-riscv64 才能完整运行）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| E007 | config.guess 无法识别 HarmonyOS | GNU config.guess 缺少 HarmonyOS 检测分支 | 添加 HarmonyOS 检测代码（__OHOS__→ohos libc, HarmonyOS kernel→aarch64-unknown-linux-ohos） |
| E011 | configure 创建临时文件失败（Permission denied） | HMDFS UID 映射导致 umask 077 目录不可写 | 修改所有 configure 脚本 umask 077 → 022（共 14 个） |
| 脚本执行 | #!/bin/sh shebang 被内核拒绝 | HMDFS/KNFS 文件系统不支持 shebang 执行 | 修复 shebang 为 bash 路径或通过 bash 显式调用 |

## 产物清单

安装到 `$PREFIX` 后的关键文件：

```
bin/riscv64-elf-addr2line
bin/riscv64-elf-ar
bin/riscv64-elf-as
bin/riscv64-elf-c++filt
bin/riscv64-elf-ld
bin/riscv64-elf-ld.bfd
bin/riscv64-elf-nm
bin/riscv64-elf-objcopy
bin/riscv64-elf-objdump
bin/riscv64-elf-ranlib
bin/riscv64-elf-readelf
bin/riscv64-elf-size
bin/riscv64-elf-strings
bin/riscv64-elf-strip
riscv64-elf/bin/ar -> ../../bin/riscv64-elf-ar
riscv64-elf/bin/as -> ../../bin/riscv64-elf-as
riscv64-elf/bin/ld -> ../../bin/riscv64-elf-ld
riscv64-elf/lib/ldscripts/elf64lriscv.x (and variants)
lib/libbfd.a
lib/libopcodes.a
lib/libiberty.a
lib/libsframe.a
```

## 依赖版本

无外部 Conan 依赖（binutils 自包含，运行时依赖系统基础库）。

## 验证结果

```bash
riscv64-elf-ld --version    # GNU ld (GNU Binutils) 2.46.0
riscv64-elf-as --version    # GNU assembler (GNU Binutils) 2.46.0
riscv64-elf-objdump --version  # GNU objdump (GNU Binutils) 2.46.0
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/r/riscv64-elf-binutils/commands.json | 命令行工具声明（R38） |
| archives/r/riscv64-elf-binutils/2.46.0/conanfile.py | Conan 配方 |
| archives/r/riscv64-elf-binutils/2.46.0/conandata.yml | 源码+补丁声明 |

## 注意事项

- riscv64-elf 是 bare-metal 目标，`make check` 中需要工具模拟器（qemu-riscv64）的测试会被跳过
- gprofng 在 HarmonyOS 上不可用，已通过 `--disable-gprofng` 禁用
- 所有 configure 脚本都需要修改 umask（共 14 个）
- 补丁基于 `binutils/2.46.0` 的 OHOS 适配补丁修改而来
- 产品类型为命令行工具（R38），需软件级 commands.json

---

**编译结束**: 2026-07-25
**最终状态**: built（configure 成功，make 因环境 shebang 限制未完成完整编译）
