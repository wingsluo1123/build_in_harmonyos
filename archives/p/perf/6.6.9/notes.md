# perf 6.6.9 适配笔记

## 编译环境
- 构建系统: makefile (custom kernel build system)
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: built

## 编译步骤

perf is part of the Linux kernel source tree (tools/perf/). The build uses the kernel's Kbuild system.

```bash
cd tools/perf
make JOBS=1 NO_LIBELF=1 NO_LIBTRACEEVENT=1 V=1
make install DESTDIR=$TEST_PREFIX prefix=/
```

Key environment:
- `JOBS=1` to avoid mkfifo (not supported on HarmonyOS HMDFS)
- `HOSTCC=clang` for host tool compilation
- gcc -> clang symlink needed for kernel build system defaults

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `#!/bin/bash` not found | HarmonyOS /bin is read-only, no bash | Patch shebang to `#!/data/service/hnp/bin/bash` |
| 2 | `make: jobserver mkfifo: Operation not permitted` | HMDFS doesn't support named pipes | Use `JOBS=1` to disable parallel jobserver |
| 3 | `gcc: inaccessible or not found` | Kernel build uses gcc for host tools | Create gcc -> clang symlink |
| 4 | `No gnu/libc-version.h found` | HarmonyOS doesn't use glibc; libelf not found triggers glibc check | Build with NO_LIBELF=1 |
| 5 | `libtraceevent is missing` | libtraceevent not available on OHOS | Build with NO_LIBTRACEEVENT=1 |
| 6 | `open() redundant mode bits; missing O_CREAT` | OHOS fortify headers reject open(path, O_RDONLY, O_NONBLOCK) | Fix to open(path, O_RDONLY | O_NONBLOCK) |

## 源码修改

1. **Shebang fix**: All scripts in tools/perf/, tools/build/, tools/scripts/, tools/lib/ with `#!/bin/bash` changed to `#!/data/service/hnp/bin/bash`
2. **builtin-daemon.c line 534**: `open(ack_path, O_RDONLY, O_NONBLOCK)` → `open(ack_path, O_RDONLY | O_NONBLOCK)`

## 依赖版本

- Linux kernel 6.6.9 source
- zlib (system, for compression support)
- Optional (disabled in this build): elfutils, openssl, zstd, slang, libcap

## 验证结果

```bash
$ ls -la perf
-rwxr-x--- 1 ... 2901896 ... perf
$ file perf
perf: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 注意事项

- perf is a command-line tool (not a library), requires commands.json (R38)
- The source tarball is the full Linux kernel (~140MB), but only tools/perf/ is built
- libtraceevent and libelf are not available on OHOS platform; features are disabled via build options
- This is not a code cut (裁剪); the software's build system is designed to work without these optional dependencies
---

**编译结束**: 2026-08-07 10:30
**最终状态**: built
