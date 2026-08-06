# Midnight Commander 4.8.30 编译笔记

## 编译环境
- 编译器: clang 15.0.4
- 构建系统: autotools (autoconf 2.73, automake 1.18.1, libtool 2.5.4, gettext 1.0)
- HarmonyOS PC (aarch64, HongMeng Kernel 1.12.0)

## 依赖
- glib2/2.88.0 (from conan ohpcd repo)
- slang/2.3.3 (from conan ohpcd repo, used instead of ncurses)
- pcre2/10.45 (transitive dependency via glib2)
- zlib/1.3.1 (transitive dependency via glib2)

## 问题解决

### 1. autoconf 2.73 "undefined or overquoted macro: dnl"
**Root cause**: autoconf 2.73 has a stricter macro checking that flags builtin m4 macros (dnl, AC_MSG_WARN, AC_MSG_ERROR) as "undefined or overquoted".
**Fix**: Add `m4_pattern_allow([dnl])`, `m4_pattern_allow([AC_MSG_WARN])`, `m4_pattern_allow([AC_MSG_ERROR])` at the beginning of configure.ac.

### 2. config.guess doesn't recognize HarmonyOS
**Root cause**: config.guess doesn't have a case for HarmonyOS (uname -s returns "HarmonyOS").
**Fix**: Patch config.guess to treat HarmonyOS as Linux (output `aarch64-unknown-linux-gnu`), and patch config.sub to add `ohos` as an alias for `linux`.

### 3. config.status "Permission denied" creating temp files
**Root cause**: config.status uses `umask 077` to create temp directories with 700 permissions. On HarmonyOS, the file system assigns directories to uid 20001006, but the build process runs as a different uid. With 700 permissions, the process can't access the directory.
**Fix**: Replace `umask 077` with `umask 022` in the configure script. This creates directories with 755 permissions, allowing the process to access them.

### 4. Conan .la files have incorrect libdir paths
**Root cause**: Conan packages were built with prefix=/, so .la files have `libdir='//lib'`. When libtool resolves dependencies, it can't find the .la files at the wrong path.
**Fix**: Remove .la files from conan cache (rename to .bak) so libtool falls back to using .a/.so files directly.

### 5. Missing libtermcap
**Root cause**: mc's configure detects that slang uses termcap and adds `-ltermcap` to MCLIBS. But libtermcap is not available on HarmonyOS.
**Fix**: Create a dummy libtermcap.a with empty implementations of termcap functions (tgoto, tgetent, tgetstr, tputs, tgetflag, tgetnum). Since slang provides its own terminal handling, the dummy functions are never called.

### 6. po/Makefile missing
**Root cause**: gettext 1.0's po/Makefile.in.in doesn't define `top_builddir`. config.status creates `po/Makefile.in` but not `po/Makefile`. The top-level Makefile expects `po/Makefile` to exist.
**Fix**: Create po/Makefile from po/Makefile.in, adding `top_builddir = ..` and fixing the config.status path.

## Configuration Summary
- Compiler: clang
- Screen library: S-Lang 2.3.3 with terminfo database
- File system: Virtual Filesystem (cpio, extfs, fish, ftp, sfs, tar)
- Internal editor: yes
- Diff viewer: yes
- Subshell support: yes
- Background operations: yes
- Charset support: yes
- Search type: glib-regexp
- X11 events support: no (not available on HarmonyOS)
---

**编译结束**: 2026-08-07 04:29
**最终状态**: built
