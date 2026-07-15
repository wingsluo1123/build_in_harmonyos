# hwinfo

Hardware detection tool from openSUSE. Detects and reports information about CPU, memory, disks, network interfaces, PCI/USB devices, and other hardware components.

Originally developed for the openSUSE distribution, hwinfo uses a library (libhd) for hardware probing and provides a command-line tool for reporting system hardware information.

## Version 25.4

Adapted for OpenHarmony PC (aarch64) platform.

### Adaptation Notes

- **version.h generation**: The Makefile's git2log script fails without a .git directory. Fixed by generating version.h manually in the Conan recipe's build() method.
- **Socket header conflict**: `sys/socket.h` and `linux/socket.h` both define `sockaddr_storage` on HarmonyOS. Fixed by defining `_UAPI_LINUX_SOCKET_H` guard before including linux headers.
- **UUID compatibility**: hwinfo expects libuuid (util-linux) API, but only ossp-uuid is available on OHOS. Created a minimal `uuid/uuid.h` header and `uuid_unparse_lower()` implementation.
- **lex/flex**: Created symlink from lex to flex (both available on the system).
- **install command**: OHOS lacks GNU `install` command. Manual file copy used instead.
