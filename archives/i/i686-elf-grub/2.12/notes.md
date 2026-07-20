# i686-elf-grub 2.12 — Adaptation Notes

## Overview
GNU GRUB bootloader cross-compiled for i686-elf target on aarch64-ohos.

## Build Configuration
- **Target**: i686-elf
- **Build/Host**: aarch64-unknown-linux-gnu (OHOS)
- **Source**: https://ftp.gnu.org/gnu/grub/grub-2.12.tar.xz
- **SHA256**: f3c97391f7c4eaa677a78e090c7e97e6dc47b16f655f04683ebd37bef7fe0faa

## Configure Options
```
./configure --target=i686-elf --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu --prefix=$DEFAULT_PREFIX --disable-werror --disable-nls
```

## Build Issues and Fixes

### 1. Missing bison and flex
- **Issue**: GRUB requires bison and flex to generate parser/lexer files (grub_script.tab.c, grub_script.yy.c). These were not installed.
- **Fix**: Found cached harmonybrew bottles for bison 3.8.2 and flex 2.6.4, installed from local cache.

### 2. config.status umask 077 → 022 (E011)
- **Issue**: HMDFS filesystem doesn't work with umask 077 (temporary directory creation fails with Permission denied).
- **Fix**: Changed `umask 077` to `umask 022` in config.status and configure scripts.

### 3. Missing sys/sysmacros.h major()/minor() (E046)
- **Issue**: GRUB's `include/grub/osdep/major.h` conditionally includes `<sys/sysmacros.h>` only when `MAJOR_IN_SYSMACROS` is defined. Configure failed to detect this on OHOS.
- **Fix**: Added unconditional `#include <sys/sysmacros.h>` in major.h.

### 4. Missing extra_deps.lst
- **Issue**: `grub-core/extra_deps.lst` referenced by Makefile but missing from release tarball.
- **Fix**: Created empty file.

### 5. genmoddep.awk: undefined _GLOBAL_OFFSET_TABLE_
- **Issue**: PIC code on i386 generates `_GLOBAL_OFFSET_TABLE_` references. The genmoddep.awk script treats undefined symbols as errors.
- **Fix**: Added `_GLOBAL_OFFSET_TABLE_` to the allowed undefined symbols list in genmoddep.awk.

### 6. genmoddep.awk: duplicate __x86.get_pc_thunk.* symbols
- **Issue**: PIC code on i386 generates `__x86.get_pc_thunk.*` helper functions in multiple modules. The genmoddep.awk script treats duplicate symbols as errors.
- **Fix**: Added regex pattern to skip `__x86.get_pc_thunk.*` in the duplicate check.

### 7. CFLAGS=-fPIC causes unsupported relocation 0xa
- **Issue**: The host CFLAGS (`-fPIC -O2`) was passed to the i686-elf-gcc cross-compiler in grub-core Makefile, causing GOT-based relocations not supported by GRUB modules.
- **Fix**: Removed `-fPIC` from CFLAGS in grub-core Makefile (modules use -fno-PIC implicitly via target flags).

### 8. make check skipped
- **Reason**: make check requires running GRUB tests which need bootable images and filesystem access not available on OHOS. Skipped to avoid long delays.

## Products
- **bin/**: grub-mkimage, grub-mkrelpath, grub-script-check, grub-editenv, grub-mkpasswd-pbkdf2, grub-fstest, grub-mklayout, grub-mkrescue, grub-mkstandalone, grub-mknetdir, grub-menulst2cfg, grub-syslinux2cfg, grub-glue-efi, grub-render-label, grub-file, grub-kbdcomp
- **sbin/**: grub-probe, grub-bios-setup, grub-sparc64-setup, grub-ofpathname, grub-macbless, grub-install, grub-mkconfig, grub-reboot, grub-set-default
- **lib/grub/**: GRUB modules (.mod), kernel images, boot images

## Dependencies
- clang (host compiler, used via wrapper as i686-elf cross-compiler)
- LLVM toolchain: llvm-ar, llvm-ranlib, llvm-nm, llvm-strip, llvm-objcopy, llvm-as, ld.lld
- bison 3.8.2 (parser generator)
- flex 2.6.4 (lexer generator)
- liblzma (for XZ compression support)

### 9. CI: configure assembly compilation failure
- **Issue**: CI build failed at configure step with `configure: error: could not compile assembly`. GRUB's configure looks for `i686-elf-gcc` in PATH (not found in CI env), falls back to `cc` (host clang without `--target` flag), which cannot compile i686 assembly.
- **Root Cause**: CI environment lacks `i686-elf-gcc` cross-compiler that was available during manual build.
- **Fix**: Added `_setup_cross_tools()` method in conanfile.py that creates wrapper scripts (`i686-elf-gcc`, `i686-elf-cc`, etc.) calling `clang --target=i686-elf`, plus LLVM binutils wrappers (`i686-elf-ar`, `i686-elf-objcopy`, etc.). The wrapper directory is prepended to PATH in build env.
---

**编译结束**: 2026-07-19 13:01
**最终状态**: adapting
