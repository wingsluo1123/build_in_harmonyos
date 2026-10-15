# Distro OpenIndiana

OpenIndiana carries `sox-14.4.2` with three patches

All three have been applied to `sox_ng`.

| Patch | Issue/Commit |
| :---- | :---: |
| [6.formats](https://github.com/OpenIndiana/oi-userland/blob/7942b0829973c7a732d67ca3e0bb240679fac40e/components/multimedia/sox/patches/6.formats.c.patch) | #170 |
| [8.libsox.c](https://github.com/OpenIndiana/oi-userland/blob/7942b0829973c7a732d67ca3e0bb240679fac40e/components/multimedia/sox/patches/8.libsox.c.patch) | 32fe572 |
| [9.disableencumbered](https://github.com/OpenIndiana/oi-userland/blob/7942b0829973c7a732d67ca3e0bb240679fac40e/components/multimedia/sox/patches/9.disableencumbered.patch) | (*) |

(*) This disables `libgsm` and `opencore-amr`, which are not encumbered.
`libgsm` has got its copyright notice back #43 and `opencore-amr` is under
the Apache v2.0 license, which is GPLv2-compatible; see [Copyright](Copyright).
