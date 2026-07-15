# Adaptation Notes - hwinfo 25.4

## Build Environment
- **Platform**: OpenHarmony aarch64
- **Compiler**: clang 15.0.4
- **Build System**: Makefile (plain make, no configure)
- **Source Version**: 25.4
- **Build Date**: 2026-07-15

## Adaptation Issues and Fixes

### 1. version.h Not Generated
**Issue**: The Makefile uses `git2log` to generate `src/hd/version.h`, but git2log fails without a `.git` directory (source extracted from tarball).
**Fix**: Generate `version.h` manually in conanfile.py's `build()` method with `#define HD_VERSION_STRING "25.4"`.

### 2. Socket Header Conflict (net.c, pppoe.c, wlan.c)
**Issue**: `sys/socket.h` defines `sockaddr_storage`, then `linux/if.h` includes `linux/socket.h` which redefines `sockaddr_storage`. On HarmonyOS, the kernel headers don't check for the userspace guard `_SYS_SOCKET_H`.
**Fix**: Define `_UAPI_LINUX_SOCKET_H` and `typedef sa_family_t __kernel_sa_family_t` after including `sys/socket.h` and before including linux headers. This prevents `linux/socket.h` from redefining `sockaddr_storage` while preserving other kernel type definitions.
**Patch**: `0002-socket-header-conflict.patch`

### 3. UUID API Incompatibility
**Issue**: hwinfo's `smbios.c` expects the libuuid (util-linux) API (`uuid_t` as `unsigned char[16]`, `uuid_unparse_lower()`), but only `ossp-uuid` is available on the OHOS artifact repository. The ossp-uuid API uses opaque pointers and different function signatures.
**Fix**: Created a minimal `uuid/uuid.h` header and `uuid_compat.c` implementation providing `uuid_t` type definition and `uuid_unparse_lower()` function. This avoids the external dependency entirely.
**Patch**: `0001-uuid-compat.patch`

### 4. lex Command Missing
**Issue**: The `src/isdn/cdb/Makefile` uses `lex` to generate `lex.yy.c`, but only `flex` is available on OHOS.
**Fix**: Created symlink `/usr/local/bin/lex -> flex`.

### 5. install Command Missing
**Issue**: OHOS lacks the GNU `install` command used by the Makefile's `install` target.
**Fix**: Manual file copy using `cp -a` in the Conan recipe's `package()` method.

### 6. -luuid Linking
**Issue**: The Makefile links the shared library with `-luuid` (`SO_LIBS = -luuid`), but no libuuid exists.
**Fix**: Set `SO_LIBS=""` when running make, since `uuid_unparse_lower` is compiled into `libhd.a` via `uuid_compat.c`.

## Build Artifacts
- `hwinfo` (125KB) - hardware detection tool
- `libhd.a` (6.9MB) - static library
- `libhd.so.25.4` (4.9MB) - shared library
- `check_hd`, `convert_hd`, `getsysinfo`, `mk_isdnhwdb` - utility tools

## Test Results
- `hwinfo --version` → outputs `25.4` ✅
