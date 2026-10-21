# SACLIB 2.2.8 / 2.2.8.1 — HarmonyOS PC (aarch64) adaptation

SACLIB is a C library of computer-algebra algorithms (arbitrary-precision
integer and polynomial arithmetic, GCD, real root isolation) from the United
States Naval Academy. This directory contains the Conan 2 recipe that builds it
for OpenHarmony / HarmonyOS PC on aarch64.

It is the first consumer of the library in this repository: `qepcad/1.74`
requires it and links `${saclib}/lib/saclibo.a` directly.

**2.2.8.1** is a re-release of the same upstream 2.2.8 tarball. It exists because
the 2.2.8 artefact left 13 dangling external references (`rounddown` ×7,
`roundup` ×6) in `lib/saclibo.a`: `include/hfloats.h` only defined those macros
for SPARC / X86_LINUX / MAC_OSX, while the OHOS port defines `_OHOS_AARCH64_`, so
the `HIP*.c` sources compiled implicit function declarations. SACLIB itself only
runs `ar`, never a link, so the defect could only appear in the first downstream
consumer that linked the archive — qepcad. `patches/0003-ohos-round-macros.patch`
adds the missing platform branch; see `notes.md` §8 for the evidence.

## What the port needed

SACLIB has no `configure`, no CMake and no Meson. Everything that is not
portable C lives in `sysdep/<target>/`, and `bin/mksysdep.pl` picks a target at
build time. There was no aarch64/OHOS target, and the x86_64 Linux one is not
usable here:

| Shipped port | Why it cannot be reused |
|--------------|-------------------------|
| `sysdep/linuxX86_64` | `sysdep.h` defines `_X86_LINUX_`, which makes `include/hfloats.h` include the glibc-only `<ieee754.h>`; its `GC.c` spills 16 registers, which is the System V AMD64 convention |
| `sysdep/linuxX86` | same, 32-bit x86 |
| `sysdep/macosX86*` | same, macOS |
| `sysdep/solarisSparc` | big-endian, SPARC assembly |

`patches/0001` therefore adds `sysdep/ohosAarch64` the way `sysdep/README`
prescribes (a new port directory plus recognition in `mksysdep.pl`) and makes the
generated makefile's assembler flags overridable, because upstream hard-codes the
GNU `as -P` option that AArch64 `as` rejects.

`patches/0002` marks SACLIB's optional `sacMain()` hook weak, so that a consumer
that defines its own `main()` can never clash with the archive member holding
SACLIB's default `main()`.

## Build flow

```
perl bin/mksysdep.pl ohosAarch64     select the port
sh sysdep/ohosAarch64/install        GC.c -> src/, sysdep.h -> include/
bin/mkmake                           generate lib/objo/makefile
bin/mklib opt CC=... AR=... RANLIB=...   compile + archive -> lib/saclibo.a
```

`bin/sconf` is only a bash wrapper around the first step; `bin/mkproto` is skipped
because the tarball's `include/sacproto.h` is byte-identical to a fresh
regeneration from the same sources. Both deviations are justified with evidence
in `notes.md` §3.6.

## Package layout

```
include/*.h          all SACLIB headers (sysdep.h included)
lib/saclibo.a        upstream name, what the QEPCAD B Makefiles link
lib/libsaclib.a      same archive, conventional name for -lsaclib / CMake
licenses/LICENSE
```

`cpp_info.libs = ["saclib"]`, `cpp_info.system_libs = ["m"]`,
`package_type = "static-library"` (QEPCAD B re-defines several SACLIB symbols, so
the library has to be linked statically).

## Files

| Path | Purpose |
|------|---------|
| `conanfile.py` | recipe: patches, upstream generator flow, packaging |
| `conandata.yml` | source URL + sha256 + patch list |
| `patches/0001-sysdep-ohos-aarch64-port.patch` | new system-dependent port for OHOS/AArch64 |
| `patches/0002-weak-sacmain-hook.patch` | weak `sacMain()` hook |
| `test_package/test.c` | 15 exact-invariant assertions (big integers, `MDHOM`, explicit `GC()`, heap lists) |
| `test_package/conanfile.py` | compiles `test.c` against the installed package and runs it |
| `test_package/MANIFEST.yml` | upstream test declaration (upstream ships none) |
| `notes.md` | full adaptation notes, W0 findings, verification evidence, next steps |
| `manifest.yaml` | archive metadata |

## Status

**Verified on device** (HarmonyOS aarch64, clang 15, Conan 2.29.1):

- `conan create` exits 0; all 1069 sources compile and `lib/saclibo.a` is
  produced (1 987 208 bytes, 1069 members).
- `test_package` passes all 15 assertions, including the three that call `GC()`
  explicitly and re-check the live big integers afterwards.

The interesting part of the port was `GC()`: the naive translation of the
x86_64 port passed 6/6 at `-O0` and failed 18/18 at `-O1`/`-O2`/`-Os` on the
device, because AAPCS64 lets the caller keep live `Word`s in the callee-saved
registers x19-x28 across the call, where a stack scan cannot see them.  The
shipped implementation uses `setjmp()` to force those registers into the frame,
and passes the address of its own local as the scan lower bound so that the
caller's 16-byte red zone is covered too.  The measurements, the isolation
experiments and the remaining follow-ups are in `notes.md` §6.
