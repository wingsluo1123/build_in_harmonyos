# redsocks 0.5 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile, no configure script)
- 编译日期: 2026-08-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 1. 下载源码 (GitHub tag release-0.5)
# 2. 应用补丁:
#    - 0001-Makefile.patch (Makefile: add HarmonyOS to Linux case pattern)
#    - 0002-base.c.patch (base.c: replace netfilter header with SO_ORIGINAL_DST define)
# 3. 构建:
LIBEVENT_PKG=<libevent_install_path>
make CC=clang \
  CFLAGS="-g -O2 -std=c99 -D_XOPEN_SOURCE=600 -D_DEFAULT_SOURCE -D_GNU_SOURCE -Wall -I$LIBEVENT_PKG/include" \
  LDFLAGS="-L$LIBEVENT_PKG/lib -Wl,-rpath,$LIBEVENT_PKG/lib" \
  LIBS="-levent_core" -j1
# 4. 安装 (手动复制):
cp redsocks $PREFIX/bin/
cp redsocks.conf.example $PREFIX/etc/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `linux/netfilter_ipv4.h` causes `sockaddr_storage` redefinition error | OHOS sysroot's `linux/socket.h` redefines `sockaddr_storage` which conflicts with `sys/socket.h` | Replaced `#include <linux/netfilter_ipv4.h>` with `#define SO_ORIGINAL_DST 80` directly in `base.c` |
| 2 | `config.h` generated without `USE_IPTABLES` | `uname` returns "HarmonyOS" not "Linux", Makefile's case pattern doesn't match | Added `HarmonyOS` to `Linux*` case pattern in Makefile |

## 源码修改

### 0001-Makefile.patch
- File: `Makefile`
- Change: Added `HarmonyOS` to the `Linux*` case pattern in `config.h` generation
- Reason: `uname` returns "HarmonyOS" on OHOS, needs to be treated as Linux for iptables support

### 0002-base.c.patch
- File: `base.c`
- Change: Replaced `#include <linux/netfilter_ipv4.h>` with inline `#define SO_ORIGINAL_DST 80`
- Reason: OHOS sysroot kernel headers conflict with libc headers when including `linux/netfilter_ipv4.h`

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libevent | 2.1.12 | Conan 制品仓 (ohpcd) |

## 验证结果

```bash
$ ./redsocks -v
redsocks/0.5
Built with libevent-2.1.12-stable
Runs  with libevent-2.1.12-stable

$ file redsocks
redsocks: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 注意事项

- redsocks is a command-line tool (not a library), package_type=application
- Upstream tests require VM networking + docker containers (squid, dante, nginx), cannot run on OHOS
- The binary links dynamically against libevent (via conan-managed RPATH)

最终状态: built
