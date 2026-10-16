# VeraCrypt 1.26.24

VeraCrypt is a disk encryption utility with a console interface.

- Upstream: https://github.com/veracrypt/VeraCrypt
- Release source: https://downloads.sourceforge.net/project/veracrypt/VeraCrypt%201.26.24/Source%20Code/VeraCrypt_1.26.24_Source.tar.bz2
- License: Apache-2.0 AND TrueCrypt-3.0
- Output: `bin/veracrypt`

The HarmonyOS PC build uses the upstream console-only `NOGUI=1` path. A small source patch adds HarmonyOS to VeraCrypt's existing Linux makefile branch because the device identifies itself with `uname -s` as `HarmonyOS` while its compiler exposes the Linux-compatible ABI.

The upstream release make target runs the built-in platform and encryption self-tests. The Conan consumer test repeats that command and suppresses its raw output; the test runner emits only the exit-status result.
