# Notes — postgresql-pllua REL_2_0_12

## Build System
PL/Lua uses PostgreSQL's PGXS (PostgreSQL Extension Build System) via a Makefile.
It requires `pg_config`, PGXS makefiles, and server headers which are NOT part of
the libpq conan package.

## Key Adaptations

### 1. pg_attribute_noreturn() Compatibility (PostgreSQL 18)
PostgreSQL 18 removed `pg_attribute_noreturn()` in favor of `pg_noreturn`.
Patch adds a compatibility define in `src/pllua.h`.

### 2. HarmonyOS umask 077 Filesystem Issue
`config.status` uses `umask 077` when creating temp directories. On HarmonyOS,
files are owned by a different uid than the process, so `umask 077` creates
inaccessible directories. Patched to `umask 022`.

### 3. LLVM Linker Binary Embedding
PL/Lua embeds Lua bytecode into .o files using `ld -r -b binary`.
LLVM's `ld.lld` requires `-m aarch64elf` to specify the target architecture.
Set `BIN_LD=ld.lld -m aarch64elf -r -b binary`.

### 4. VPATH Detection
The Makefile's VPATH detection triggers incorrectly on HarmonyOS filesystem.
Disabled with `VPATH=`.

### 5. Lua Interpreter for Build-time Codegen
PL/Lua needs `lua` and `luac` to generate headers (functable.h, errcodes.h)
and compile compat.lua to bytecode. The conan lua package only provides headers
and library, so the recipe builds lua/luac from the Lua 5.4.8 source.

## Dependencies
- libpq/18.1 — PostgreSQL client library
- lua/5.4.8 — Lua headers and library (static)
- PostgreSQL 18.1 source — for pg_config, PGXS, server headers (build-only)
- Lua 5.4.8 source — for lua/luac interpreter (build-only)

## Build Artifacts
- lib/pllua.so — PostgreSQL extension shared library
- share/extension/ — control files and SQL scripts
- include/server/extension/pllua/ — extension header files

## 结束
status: closed
---

**编译结束**: 2026-08-09 01:13
**最终状态**: built
