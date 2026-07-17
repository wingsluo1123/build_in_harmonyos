# Adaptation Notes — ax25-apps 0.0.8-rc5

## Source Info
- Source: Debian pool (ax25-apps_0.0.8-rc5+git20230513+afc4a5f.orig.tar.xz)
- SHA256: dc32cf12d05ee516adefefdf81293ed2be6d79f2137155ae6bccdf2fde7029a9
- Build system: autotools (configure.ac + Makefile.am)

## Dependencies
- libax25/0.0.12-rc5 (from local conan cache, static build)
- ncursesw (system installed at /storage/Users/currentUser/usr/local)
- libiconv (system installed, needed by call binary)

## Platform Adaptations

### 1. E129: umask 077 HMDFS fix
- File: configure (and generated config.status)
- Fix: `sed -i 's/umask 077/umask 022/g' configure`
- Reason: HMDFS filesystem sets setgid bit on new directories; umask 077 creates drwx--S--- which blocks owner writes

### 2. termio.h -> termios.h
- File: ax25ipd/io.c
- Fix: Replace `#include <termio.h>` with `#include <termios.h>`, `struct termio` -> `struct termios`, `ioctl(TCGETA/TCSETA)` -> `tcgetattr/tcsetattr`
- Reason: termio.h not available on OHOS (POSIX deprecated), termios.h is the replacement

### 3. Remove linux/ax25.h include
- File: call/yapp.c
- Fix: Remove `#include <linux/ax25.h>` (unused, causes sockaddr_storage redefinition on OHOS)
- Reason: OHOS sysroot has conflicting definitions between linux/socket.h and sys/socket.h

### 4. Add time.h include to call.h
- File: call/call.h
- Fix: Add `#include <time.h>` at the top
- Reason: call.h uses time_t but doesn't include the header

### 5. ncursesw header symlink
- Created: /storage/Users/currentUser/usr/local/include/ncursesw/ncurses.h -> ../ncurses.h
- Reason: call.c includes <ncursesw/ncurses.h> but system ncurses has flat header layout

### 6. Add -liconv to call_LDADD
- File: call/Makefile (generated from Makefile.am)
- Fix: `call_LDADD = $(NCURSES_LIB) $(AX25_LIB) -liconv`
- Reason: call binary uses iconv functions (libiconv_open, libiconv, libiconv_close) which need -liconv

## Build Environment
- CC=cc (clang 15.0.4)
- CFLAGS=-I{libax25_include} -I/usr/local/include
- LDFLAGS=-L{libax25_lib} -L/usr/local/lib

## Result
- All 6 binaries compiled and installed: call, listen, ax25ipd, ax25rtd, ax25rtctl, ax25mond
- All ELF64 AArch64
- libax25 statically linked (shared=False)
- call: depends on libiconv.so.2, libc.so
- Others: depend only on libc.so
---

**编译结束**: 2026-07-17 18:18
**最终状态**: published
