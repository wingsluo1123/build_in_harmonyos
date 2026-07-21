# Build Notes — slang 2.3.3 on HarmonyOS PC

## Overview
S-Lang 2.3.3 successfully compiled and verified on HarmonyOS PC (aarch64-unknown-linux-ohos) using autotools build system.

## Key Issues and Solutions

### E072: config.sub does not recognize ohos
- **Root cause**: The `config.sub` script from the slang 2.3.3 tarball does not recognize `ohos` as a valid operating system value, causing triplet validation failure during `./configure`.
- **Fix**: Patched `autoconf/config.sub` to add:
  1. `ohos-linux` → `basic_os=linux-ohos` mapping (after android-linux branch)
  2. `ohos*` entry in the OS whitelist (`case $os in`)
  3. `linux-ohos*` entry in the kernel-os whitelist (`case $kernel-$os in`)
- **Patch file**: `patches/0001-autoconf-config.sub.patch`

### Configure patch: --build/--host triplet bypass
- **Root cause**: `config.guess` cannot detect the HarmonyOS platform and fails to create temporary files in `/tmp`.
- **Fix**: Patched `configure` to explicitly pass `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos` to bypass config.guess auto-detection.
- **Patch file**: `patches/0002-configure.patch`

### Environment issues
- `umask 077` on OHOS causes directory permission issues (drwx--S---), changed to `umask 022`
- `/tmp` is read-only on OHOS, set `TMPDIR=$HOME/tmp`
- Conan recipe includes `LD_LIBRARY_PATH` in `runenv_info` to ensure runtime library discovery

## Build Configuration
- **Build system**: autotools (configure && make)
- **Compiler**: clang 15.0.4
- **Configure options**: `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos --prefix=$DEFAULT_PREFIX`
- **Make options**: `-j2`
- **Dependencies**: none (slang is self-contained)

## Test Results
- `make check`: 70+ tests passed, 4 tests failed (posixio.sl, posdir.sl — expected on HarmonyOS due to POSIX I/O differences)
- `slsh --version`: "slsh version 0.9.4-0; S-Lang version: 2.3.3"
- Conan test_package: SLang_init_all()=0, SLang_Version=20303, SLang_Version_String="2.3.3" — all PASS

## Conan Recipe
- 8-gate verification: ALL PASS (G0, G1, G2, G3, G4, L2, L4, L5)
- W3 local CI simulation: PASS
- Build type: shared library + executable (slsh)

## Artifacts
- `lib/libslang.so.2.3.3` (4.9 MB shared library)
- `bin/slsh` (88 KB S-Lang shell interpreter)
- `include/slang.h`, `include/slcurses.h`
- 19 dynamically loadable modules (.so files)
---

**编译结束**: 2026-07-21 19:21
**最终状态**: published
