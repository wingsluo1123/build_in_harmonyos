# notes.md — passt 2026_07_28.f8df3f1 adaptation notes

## Overview

passt (Plug A Simple Socket Transport) is a user-mode networking tool for VMs
and containers. It replaces slirp/slirp4netns/libslirp. Zero third-party
dependencies (only standard C library + Linux kernel headers).

## Build System

Plain Makefile — no configure, no cmake, no autotools.
- `make CC=clang` builds: passt, pasta (symlink), pesto, passt-repair
- `make install DESTDIR=... prefix=...` installs to staging

## OHOS Platform Adaptation (5 fixes)

### Fix 1: seccomp.sh fmt -t (toybox incompatibility)
- **File**: seccomp.sh
- **Error**: `fmt: Unknown option 't'` — OHOS toybox `fmt` doesn't support GNU `-t`
- **Fix**: Removed `-t` flag (cosmetic only, seccomp header generation unaffected)

### Fix 2: sockaddr_storage redefinition
- **Files**: passt.h, netlink.c
- **Error**: `redefinition of 'sockaddr_storage'` — OHOS sysroot defines it in both
  `<sys/socket.h>` and `<linux/socket.h>` without cross-guards
- **Fix**: Define `_UAPI_LINUX_SOCKET_H` + typedef `__kernel_sa_family_t` before
  `#include <linux/un.h>` (passt.h) and `#include <linux/netlink.h>` (netlink.c)

### Fix 3: struct udphdr incomplete
- **File**: checksum.c
- **Error**: `incomplete definition of type 'struct udphdr'` — OHOS `<linux/udp.h>`
  defines `struct __kernel_udphdr`, not `struct udphdr`
- **Fix**: Replace `#include <linux/udp.h>` with `#include <netinet/udp.h>`

### Fix 4: close_range / CLOSE_RANGE_UNSHARE undeclared
- **File**: isolation.c
- **Error**: `use of undeclared identifier 'CLOSE_RANGE_UNSHARE'` —
  `close_range()` not declared in OHOS libc headers
- **Fix**: Add `#include <linux/close_range.h>` + `extern int close_range(...)`

### Fix 5: vring_need_event undefined (linker)
- **File**: virtio.c
- **Error**: `undefined symbol: vring_need_event` — OHOS `<linux/virtio_ring.h>`
  missing this function
- **Fix**: Added `static inline` definition copied from upstream kernel header

## Upstream Tests

- **Smoke tests** (test/smoke/smoke.sh via exeter): 4 tests, all FAIL on OHOS
  - Root cause: `isolate_initial()` reads `/proc/self/ns/user` (not available on OHOS)
  - This is a runtime limitation, not a build issue
- **Full test suite** (test/run): requires qemu, tmux, network namespaces — not runnable on OHOS
- **pesto --version**: Works (prints version + copyright, exits via seccomp)

## HarmonyOS-Specific Tests (鸿蒙特有测试)

- **AArch64 ELF architecture verification**: Verifies pesto binary is built for
  OHOS arm64 (AArch64) platform. Upstream Linux builds are x86_64; AArch64 ELF
  is specific to HarmonyOS PC. Uses `readelf -h` to check ELF Machine field.

## Binary Inventory

| Binary | Size | Description |
|--------|------|-------------|
| passt | 383KB | Main daemon (passt + pasta modes) |
| pasta | symlink → passt | Namespace mode |
| pesto | 51KB | Port mapping helper |
| passt-repair | 27KB | TCP_REPAIR migration helper |

## Dependencies

None — zero third-party dependencies (confirmed by Makefile, README, source code).
---

**编译结束**: 2026-09-21 00:25
**最终状态**: built
