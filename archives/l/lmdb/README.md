# LMDB for HarmonyOS

## Overview

LMDB (Lightning Memory-Mapped Database) is a Btree-based database management library modeled loosely on the BerkeleyDB API. It is part of the OpenLDAP project.

## Software Info

| Field | Value |
|-------|-------|
| Name | lmdb |
| Version | 0.9.35 |
| Homepage | https://git.openldap.org/openldap/openldap |
| License | OpenLDAP |
| Build System | Makefile (plain, no autotools/cmake) |

## HarmonyOS Environment

| Field | Value |
|-------|-------|
| OS | HarmonyOS |
| Arch | aarch64 |
| Compiler | clang (LLVM) |

## Build Command

```bash
make -j1 CC=clang XCFLAGS="-DMDB_USE_ROBUST=0" liblmdb.a
make -j1 CC=clang XCFLAGS="-DMDB_USE_ROBUST=0" liblmdb.so
make install DESTDIR=$DESTDIR CC=clang prefix=$PREFIX XCFLAGS="-DMDB_USE_ROBUST=0"
```

## Key Adaptation

OpenHarmony musl libc does not support robust mutex (pthread_mutexattr_setrobust and
pthread_mutex_consistent). LMDB uses robust mutex for inter-process crash recovery.
Disabling it with `-DMDB_USE_ROBUST=0` allows LMDB to compile and function on HarmonyOS.

## Products

- lib/liblmdb.a, lib/liblmdb.so (libraries)
- include/lmdb.h (header)
- bin/mdb_stat, bin/mdb_copy, bin/mdb_dump, bin/mdb_load (tools)

## Test Results

| Test | Result |
|------|--------|
| mtest2 (B+tree insert/delete/cursor) | PASS |
| mdb_stat -V | LMDB 0.9.35: (Jan 27, 2026) |
| test_package (put/get API) | PASS |
