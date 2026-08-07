# perf 6.6.9 适配笔记

## 编译环境
- 构建系统: makefile (custom, kernel tools/perf/)
- 编译日期: 2026-08-07
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤

1. 下载 Linux 6.6.9 内核源码 (Tsinghua mirror, ~214MB)
2. 下载 Linux 5.15 内核源码用于提取 libtraceevent (~186MB)
3. 从 5.15 内核提取 tools/lib/traceevent/ 并打补丁去除内核头文件依赖
4. 编译 libtraceevent (静态库 + 共享库)
5. 安装 libtraceevent 到 $DEFAULT_PREFIX, 创建 pkg-config 文件
6. 通过 conan 安装 elfutils/0.195, slang/2.3.3, libcap/2.69 等依赖
7. 编译 perf: `make CC=clang HOSTCC=clang WERROR=0 EXTRA_CFLAGS="-D__kernel_sa_family_t=sa_family_t -I$PREFIX/include" -j1`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libtraceevent not found | 6.6.9 内核不再包含 tools/lib/traceevent/ (6.0+移除) | 从 5.15 内核提取并自行编译 |
| 2 | event-parse.c: linux/time64.h not found | 内核头文件依赖 | 移除 #include <linux/time64.h> (userspace 不需要) |
| 3 | trace-seq.c: asm/bug.h not found | 内核头文件依赖 | 替换为本地 WARN_ONCE/unlikely 宏定义 |
| 4 | qsort_r undefined symbol | OHOS/musl 不提供 qsort_r | 替换为 qsort + static context variable |
| 5 | __kernel_sa_family_t unknown type | OHOS sysroot 未定义此类型 | 添加 -D__kernel_sa_family_t=sa_family_t |
| 6 | open() redundant mode bits warning | OHOS fortify 头文件更严格 | 设置 WERROR=0 |
| 7 | libelf.h not found | 系统未安装 elfutils | 通过 conan 安装 elfutils/0.195 |

## 源码修改

1. **0001-fix-qsort_r-for-ohos.patch**: 替换 util/symbol-elf.c 中的 qsort_r 调用为 qsort + 静态变量
2. **0002-libtraceevent-remove-kernel-deps.patch**: 移除 libtraceevent 的 linux/time64.h 和 asm/bug.h 依赖

## 依赖版本

- elfutils/0.195 (conan artifact repo)
- zlib/1.3.1 (conan artifact repo)
- bzip2/1.0.8 (conan artifact repo)
- slang/2.3.3 (conan artifact repo)
- openssl/1.1.1w (conan artifact repo)
- libcap/2.69 (conan artifact repo)
- libtraceevent 1.1.0 (from linux-5.15 kernel source, built locally)

## 验证结果

```bash
$ file perf
perf: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ ls -lh perf
-rwxr-x--- 1 ... 10M ... perf
```

## 注意事项

- libtraceevent 不在 conan 制品仓中, 通过从 5.15 内核源码提取并编译解决
- perf 二进制需要签名才能在 OHOS 上运行 (ELF 签名要求)
- 构建产物包含可执行文件, 需要创建 commands.json (R38)
---

**编译结束**: 2026-08-08 00:45
**最终状态**: built
