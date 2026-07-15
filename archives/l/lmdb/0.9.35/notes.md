# lmdb 0.9.35 — Adaptation Notes

## Build System
Plain Makefile (no autotools, no cmake).

## Key Adaptation
OpenHarmony musl libc does not support robust mutex (pthread_mutexattr_setrobust and pthread_mutex_consistent).
LMDB uses robust mutex by default for inter-process crash recovery. Disabling it with `-DMDB_USE_ROBUST=0`
allows LMDB to compile and function on HarmonyOS, at the cost of crash recovery semantics.

## Build Command
```bash
make -j1 CC=clang XCFLAGS="-DMDB_USE_ROBUST=0" liblmdb.a
make -j1 CC=clang XCFLAGS="-DMDB_USE_ROBUST=0" liblmdb.so
```

## Products
- lib/liblmdb.a (static library)
- lib/liblmdb.so (shared library)
- include/lmdb.h (header)
- bin/mdb_stat, bin/mdb_copy, bin/mdb_dump, bin/mdb_load (tools)

## Test
- mtest2: B+tree insert/delete/cursor iteration — passes
- mdb_stat -V: prints version "LMDB 0.9.35: (Jan 27, 2026)"

## No Dependencies
LMDB is self-contained (only depends on pthread, which is part of the system libc).
---

**编译结束**: 2026-07-15 23:06
**最终状态**: built
