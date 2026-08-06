# haproxy 3.2.0 Adaptation Notes

## Build System
- GNU Makefile, TARGET=linux-musl

## Dependencies
- openssl/3.5.6.1, zlib/1.3.1.1, pcre2/10.45

## Patches
1. 0001-include-haproxy-compat.h.patch — fix sockaddr_storage redefinition
2. 0002-src-thread.c.patch — replace pthread_setaffinity_np with sched_setaffinity

## Build Flags
- USE_OPENSSL=1 USE_ZLIB=1 USE_PCRE2=1 USE_THREAD=1 USE_PROMEX=1
---

**编译结束**: 2026-08-07 02:45
**最终状态**: built
