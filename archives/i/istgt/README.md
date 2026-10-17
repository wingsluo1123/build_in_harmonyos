# istgt

iSCSI target daemon — userspace iSCSI target (RFC 3720) implementation with
SPC-3 (SCSI Primary Commands - 3) based logical unit emulation. Supports
disk / CD-ROM / tape / pass-through logical units exported over iSCSI, with
a CLI control tool (`istgtcontrol`) for runtime configuration.

- Upstream: https://sourceforge.net/projects/istgt/ （原始站点 peach.ne.jp 已消亡）
- License: BSD-2-Clause
- Language: C
- Build system: autotools（2011 年预生成 configure，无需 autogen）

## Versions

| Version | Status | Built |
|---------|--------|-------|
| 0.4-20111008 | built | 2026-10-16 |
