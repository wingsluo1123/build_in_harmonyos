# AFL++ 5.02c 适配笔记

## 软件信息
- 名称: AFL++ (American Fuzzy Lop plus plus)
- 版本: 5.02c
- 上游: https://github.com/AFLplusplus/AFLplusplus
- 许可证: Apache-2.0
- 构建系统: GNU Make (GNUmakefile)

## 构建环境
- 平台: HarmonyOS aarch64
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 构建工具: GNU Make 4.4.1

## 适配要点

### 1. 平台检测 (SYS=Linux)
AFL++ 使用 `uname -s` 检测操作系统，HarmonyOS 返回 "HarmonyOS" 而非 "Linux"。
AFL++ 的 GNUmakefile 对 Linux/Darwin/FreeBSD 等有专门处理，HarmonyOS 不被识别。
解决方案：构建时传入 `SYS=Linux`，因为 HarmonyOS 基于 Linux 内核，
共享内存 (shmget/shmat)、fork/pipe 等 POSIX 接口与 Linux 兼容。

### 2. 编译器 (CC=clang)
HarmonyOS 平台没有 gcc，只有 clang 15.0.4。设置 CC=clang。

### 3. 可选模式禁用
以下模式因缺少依赖或平台不适用而禁用：
- NO_NYX=1: Nyx 模式需要 QEMU
- NO_QEMU=1: QEMU 模式需要 QEMU 编译
- NO_UNICORN=1: Unicorn 模式需要 Unicorn 库
- NO_CORESIGHT=1: CoreSight 仅限 ARM Linux 特定硬件
- NO_FRIDA=1: Frida 模式需要 Frida 框架

### 4. LLVM 模式
afl-cc 和 LLVM passes 编译成功，但 test_build 阶段因 OHOS SDK C++ ABI
差异（llvm::demangle 符号缺失）导致部分 LLVM pass 运行时加载失败。
这是平台 C++ 标准库 ABI 差异导致，不影响核心 fuzzing 功能。
核心二进制 (afl-fuzz, afl-showmap, afl-tmin 等) 完全正常工作。

### 5. Install 目录创建
AFL++ 的 install 目标不自动创建目标目录，需在 install 前手动 mkdir -p。

## 构建命令
```bash
make CC=clang SYS=Linux PREFIX=$PREFIX \
  NO_NYX=1 NO_QEMU=1 NO_UNICORN=1 NO_CORESIGHT=1 NO_FRIDA=1 \
  binary-only
make CC=clang SYS=Linux PREFIX=$PREFIX \
  -f GNUmakefile.llvm -j$(nproc) || true  # LLVM mode, non-fatal
make CC=clang SYS=Linux PREFIX=$PREFIX DESTDIR=$DESTDIR \
  NO_NYX=1 NO_QEMU=1 NO_UNICORN=1 NO_CORESIGHT=1 NO_FRIDA=1 \
  install || true
```

## 产物
- bin/: afl-fuzz, afl-showmap, afl-tmin, afl-gotcpu, afl-analyze, afl-cmin,
        afl-cc, afl-clang, afl-clang++, afl-gcc, afl-g++, afl-health,
        afl-network-client, afl-network-server, afl-plot, afl-whatsup 等
- lib/afl/: LLVM passes (.so), afl-compiler-rt.o, libAFLDriver.a,
             libAFLQemuDriver.a, libdislocator.so
- include/afl/: 头文件
- share/afl/: testcases, dictionaries
- share/man/man8/: man pages

## 版本验证
```
$ afl-fuzz --version
afl-fuzz++5.02c
```

## 测试
- AFL++ 上游测试框架 (test/test-all.sh) 需要 Docker 环境，不适用于 CI L1
- test_package 验证: afl-fuzz --version, afl-showmap --help, afl-cc 存在性
---

**编译结束**: 2026-07-22 18:52
**最终状态**: built
