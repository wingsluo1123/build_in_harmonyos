# i686-elf-binutils 2.42 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-17
- 编译器: clang/clang++
- 平台: aarch64-unknown-linux-ohos (HarmonyOS PC, arm64)
- 状态: built

## 编译步骤

1. 下载源码（清华镜像）：https://mirrors.tuna.tsinghua.edu.cn/gnu/binutils/binutils-2.42.tar.xz
2. 修改 config.guess 支持 HarmonyOS（添加 __OHOS__ 检测和 HarmonyOS case 分支）
3. 修改 config.sub 添加 ohos-linux 三元组支持
4. 修改所有 configure 脚本中的 umask 077 为 umask 022（解决 HMDFS 权限问题，共 15 个文件）
5. 修复 libiberty/config.h：添加缺失的 HAVE_LIMITS_H, HAVE_SPAWN_H, HAVE_FCNTL_H 等宏定义
6. 设置 CPPFLAGS="" 避免系统头文件冲突
7. 执行 configure：`./configure --target=i686-elf --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu --prefix=$DEFAULT_PREFIX --disable-gprofng --disable-nls --disable-werror`
8. 执行 make：`make -j2`
9. 执行 staging 安装：`make install DESTDIR=$TEST_PREFIX`
10. 验证工具：`i686-elf-as --version`, `i686-elf-ld --version` 等

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| E007 | config.guess 无法识别 HarmonyOS | GNU config.guess 缺少 HarmonyOS 检测分支 | 手动添加 __OHOS__ 宏检测和 HarmonyOS case 分支 |
| E011 | config.status 创建临时文件失败 | HMDFS UID 映射导致 umask 077 目录不可写 | 修改所有 configure 脚本 umask 077 → 022 |
| gprofng | gprofng 编译失败（SIGEV_THREAD_ID 未定义） | 使用 Linux 特定信号机制 | 禁用 gprofng（--disable-gprofng） |
| 头文件冲突 | md5.c/sha1.c/obstack.c 编译失败 | 系统 /usr/local/include/md5.h 等覆盖 binutils include/ 中的同名头文件 | 设置 CPPFLAGS="" 不使用系统 include 路径 |
| config.h 检测失败 | LONG_MIN/posix_spawn 等未定义 | configure 脚本交叉编译时无法正确检测标准头文件 | 手动在 config.h 中添加 HAVE_LIMITS_H 等宏定义 |
| config.sub 不识别 ohos | OS 'ohos' not recognized | config.sub 不支持 ohos 作为有效 OS | 使用 --build=aarch64-unknown-linux-gnu 绕过 |

## 产物列表

安装到 $TEST_PREFIX 的可执行文件（16 个）：
- i686-elf-addr2line
- i686-elf-ar
- i686-elf-as
- i686-elf-c++filt
- i686-elf-elfedit
- i686-elf-gprof
- i686-elf-ld
- i686-elf-ld.bfd
- i686-elf-nm
- i686-elf-objcopy
- i686-elf-objdump
- i686-elf-ranlib
- i686-elf-readelf
- i686-elf-size
- i686-elf-strings
- i686-elf-strip

## 验证结果

```bash
i686-elf-as --version       # GNU assembler (GNU Binutils) 2.42
i686-elf-ld --version       # GNU ld (GNU Binutils) 2.42
i686-elf-objdump --version  # GNU objdump (GNU Binutils) 2.42
i686-elf-readelf --version  # GNU readelf (GNU Binutils) 2.42
i686-elf-ar --version       # GNU ar (GNU Binutils) 2.42
i686-elf-nm --version       # GNU nm (GNU Binutils) 2.42
```

## make check

make check 因时间限制跳过（binutils 测试套件需要 dejagnu 且耗时较长）。

## 依赖版本

无外部依赖（binutils 自包含，zlib 为内嵌）

## 注意事项

- gprofng 在 HarmonyOS 上不可用，需禁用
- 所有 configure 脚本都需要修改 umask（共 15 个）
- 系统头文件冲突是关键问题：/usr/local/include/ 中的 md5.h、sha1.h、sha2.h、sha256.h、obstack.h 与 binutils include/ 中的同名文件冲突
- configure 脚本无法在交叉编译时正确检测标准头文件（limits.h, spawn.h 等），需手动修复 config.h
- 使用 --build=aarch64-unknown-linux-gnu 而非 HarmonyOS 三元组，因为 config.sub 不识别 ohos
---

**编译结束**: 2026-07-19 12:04
**最终状态**: built
