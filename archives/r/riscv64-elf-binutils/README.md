# riscv64-elf-binutils

GNU Binutils 的 RISC-V 64位裸机交叉编译版本。提供 RISC-V bare-metal ELF 目标平台的汇编器、链接器、目标文件工具等。

## 概述

riscv64-elf-binutils 是标准 GNU Binutils 的一个交叉编译版本，运行在 **aarch64-linux-ohos** 主机上，目标平台为 **riscv64-elf**（RISC-V 64位 bare-metal ELF）。

## 包含的工具

所有工具都以 `riscv64-elf-` 为前缀：

| 工具 | 功能 |
|------|------|
| riscv64-elf-ld | RISC-V ELF 链接器（链接脚本在 riscv64-elf/lib/ldscripts/） |
| riscv64-elf-as | RISC-V 汇编器 |
| riscv64-elf-ar | 归档创建器 |
| riscv64-elf-nm | 符号列表工具 |
| riscv64-elf-objcopy | 目标文件复制和格式转换 |
| riscv64-elf-objdump | 目标文件信息转储 |
| riscv64-elf-readelf | ELF 文件信息读取 |
| riscv64-elf-ranlib | 归档索引生成 |
| riscv64-elf-size | 段大小查看 |
| riscv64-elf-strings | 可打印字符串提取 |
| riscv64-elf-strip | 符号剥离 |
| riscv64-elf-c++filt | C++ 名称还原 |
| riscv64-elf-addr2line | 地址到源码行转换 |

## 构建系统

- **构建系统**: autotools
- **配置**: `--target=riscv64-elf --host=aarch64-linux-ohos --build=aarch64-linux-ohos`
- **编译器**: clang/clang++

## OHOS 适配

基于 `binutils/2.46.0` 的 OHOS 适配补丁，包括：
- config.guess/config.sub: HarmonyOS 系统识别（E007）
- 所有 configure 脚本: umask 077→022（HMDFS 兼容，E011）
- `--disable-gprofng`: gprofng 使用 SIGEV_THREAD_ID，OHOS 不可用

## 安装

```bash
# 使用 Conan 安装
conan install --requires=riscv64-elf-binutils/2.46.0 -r=ohpcd

# 或下载预编译包
curl -fsSL "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh" | sh -s -- riscv64-elf-binutils 2.46.0
```

## 环境变量

安装后可通过以下环境变量在交叉编译中使用：
- `RISCV64_ELF_BINUTILS_PATH` — 工具目录（bin/）
- `RISCV64_ELF_LD` — ld 完整路径
- `RISCV64_ELF_AS` — as 完整路径
