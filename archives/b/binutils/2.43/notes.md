# binutils 2.43 i686-elf 交叉编译适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built
- 目标平台: i686-elf (交叉编译)
- 主机平台: aarch64-linux (OHOS)

## 编译步骤

1. 源码路径: /storage/Users/currentUser/builds/binutils-2.43
2. 配置交叉编译:
   ```bash
   mkdir build && cd build
   ../configure --target=i686-elf --prefix=$DEFAULT_PREFIX --disable-gprofng --disable-nls --enable-interwork --enable-multilib
   ```
3. 编译: `make -j2`
4. 安装: `make install`
5. 验证: `i686-elf-ld --version`, `i686-elf-as --version`, `i686-elf-objdump --version`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| - | 无重大问题 | binutils 2.43 交叉编译到 i686-elf 目标非常成熟稳定 | 标准交叉编译流程，无需额外补丁 |

## 源码修改

无 - 标准交叉编译无需修改源码

## 依赖版本

无外部依赖（binutils 自包含）

## 验证结果

```bash
/storage/Users/currentUser/builds/binutils-2.43/i686-elf-cross/bin/i686-elf-ld --version
# GNU ld (GNU Binutils) 2.43

/storage/Users/currentUser/builds/binutils-2.43/i686-elf-cross/bin/i686-elf-as --version
# GNU assembler (GNU Binutils) 2.43
# This assembler was configured for a target of `i686-elf'.

/storage/Users/currentUser/builds/binutils-2.43/i686-elf-cross/bin/i686-elf-objdump --version
# GNU objdump (GNU Binutils) 2.43
```

## 产出物路径
- 交叉工具链二进制: /storage/Users/currentUser/builds/binutils-2.43/i686-elf-cross/bin/
- 包含 16 个工具: i686-elf-addr2line, i686-elf-ar, i686-elf-as, i686-elf-c++filt, i686-elf-elfedit, i686-elf-gprof, i686-elf-ld, i686-elf-ld.bfd, i686-elf-nm, i686-elf-objcopy, i686-elf-objdump, i686-elf-ranlib, i686-elf-readelf, i686-elf-size, i686-elf-strings, i686-elf-strip

## 注意事项
- 交叉编译到 i686-elf (ELF 裸机) 目标不需要操作系统适配补丁
- --disable-gprofng 因为 gprofng 需要特定信号机制
- --disable-nls 简化编译
---

**编译结束**: 2026-07-19 02:13
**最终状态**: built
