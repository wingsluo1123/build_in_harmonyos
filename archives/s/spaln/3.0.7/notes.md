# spaln 3.0.7 — adaptation notes (OpenHarmony PC / aarch64)

## 1. Source identity

| | |
|---|---|
| Upstream project | https://github.com/ogotoh/spaln |
| Official tag | `ver.3.0.7` (upstream tags are spelled `ver.X.Y.Z`) |
| URL used | `https://github.com/ogotoh/spaln/archive/refs/tags/ver.3.0.7.tar.gz` |
| HTTP status | `200` (redirects to the byte-identical `https://codeload.github.com/ogotoh/spaln/tar.gz/refs/tags/ver.3.0.7`) |
| Size | 22 458 478 bytes |
| sha256 | `391de895a6bcfc426edb661348e7ab55107c5c7d726411851ef3c1df5226ba20` |
| License | GPL-2.0-or-later (`LICENSE` + `COPYING` in the archive) |
| Release date of the tag | 2025-05-22 (`version = "3.0.7"`, `date = 250522` in `src/spaln.cc`) |

Note the upstream tag naming: `v3.0.7` and `3.0.7` both return HTTP 404; only
`ver.3.0.7` exists.  `https://api.github.com/repos/ogotoh/spaln/tags` lists it.

## 2. What upstream ships

* `src/` — ~50 C++ translation units plus a hand-written `configure` shell
  script (not autoconf) and `Makefile.in`.  `configure` substitutes
  `table_dir` / `alndbs_dir` into `iolib.src` → `iolib.h` and `dbs.src` →
  `dbs.h`, i.e. **the parameter-table path is compiled into the binaries**.
* `table/` — 279 species parameter files/directories (~40 MB), including the
  pre-built `mdm_cmp` and `mdm_mtx` matrices.
* `seqdb/`, `perl/` — sample sequence databases and helper scripts.
* `spaln.1`, `sortgrcd.1`, `doc/`, `README.md`, `makessp.md`.
* **No automated test suite.**  `src/Makefile.in` has a `test:` target whose
  entire recipe is `./test.sh`, and no `test.sh` exists anywhere in the release
  archive (`find . -name 'test.sh'` → 0 hits).  The target is therefore not
  runnable, by anyone.

## 3. Build-system adaptation

Four things had to be handled; **no source patch was needed**, so `patches/`
does not exist and `conandata.yml` has an empty `patches:` map.

1. **`-march=native`.**  `src/configure` sets
   `CFLAGS=${CFLAGS-"-O3 -march=native"}` on Linux.  During a cross build
   `-march=native` describes the x86_64 build host and is wrong.  The script
   only uses that default when `CFLAGS` is empty, so the recipe exports an
   explicit `CFLAGS` (`-O3` plus the dependency `-I` directories) instead of
   patching the file.

2. **Hard-coded link libraries.**  `Makefile.in` has
   `LLIB = -lpthread -lm -lz` and
   `GLIB = -L/usr/local/lib -lgsl -lgslcblas $(LLIB)`.  `configure` only
   rewrites the `ILIB` line, which does not exist in `Makefile.in`, so `-lz`
   survives configure pointing at build-machine paths.  Both variables are
   overridden on the `make` command line with `-L`/`-l` flags derived from the
   Conan `zlib` and `gsl` packages.

3. **The default make goal is `basis`, not `all`.**  `basis` builds only
   `PROG_B` (`spaln sortgrcd makmdm makdbs`); `all` additionally builds
   `PROG_A` (`dvn exinpot kmers npssm rdn utn`) and `PROG_F`
   (`fitild compild decompild plotild`).  The recipe builds `all` with
   `PROG="spaln sortgrcd makmdm makdbs dvn exinpot kmers npssm rdn utn"` so the
   package is complete apart from `PROG_F` (next point).

4. **`PROG_F` cannot be built against the OHOS libc.**  The four
   distribution-fitting tools and their shared unit `ildpdf.cc`/`ildpdf.h` are
   the only part of the tree that uses glibc-only libc entry points, and they
   are also the only consumers of GSL:

   | symbol | status on OHOS musl | evidence |
   |---|---|---|
   | `exp10()` | not declared in `<math.h>` at all, with or without `_GNU_SOURCE` | `grep -n exp10 $SYSROOT/usr/include/math.h` → 0 hits; clang error `use of undeclared identifier 'exp10'` in `ildpdf.h:273,277,278,308,318`, `fitild.cc:658`, `plotild.cc:34` |
   | `drand48_r()`, `struct drand48_data` | do not exist | clang error `variable has incomplete type 'struct drand48_data'`; `nm -D libc.so` exports `drand48` only, no `drand48_r` |
   | `<gsl/*.h>` | not used anywhere outside `PROG_F`/`ildpdf.h` | `grep -ln 'gsl/' *.cc *.h` → only `decompild.cc`, `fitild.cc`, `ildpdf.h` |

   This is not a build-flag problem: it needs source-level replacement of a
   glibc-internal reentrant PRNG.  Upstream itself treats the same reduced set
   as a supported configuration — `Makefile.in` carries
   `# for MACOS uncomment below line` / `#PROG = $(PROG_B) $(PROG_A)`, and the
   `install` target copies `PROG_F` only `if [ -s fitild ]`.  Consequently the
   package ships the 10 programs that README.md documents, GSL is **not**
   declared as a dependency (it would be a dead dependency), and the follow-up
   for a future PR is a small libc-compat patch (`exp10` → `pow(10, x)` plus a
   48-bit LCG `drand48_r` fallback) if the fitting tools are wanted.

5. **`make install` cannot be used.**  Its recipe copies the binaries, copies
   `table/` and `seqdb/`, and then **executes the freshly cross-compiled
   `makmdm`** (`./makmdm $(TABDIR)`) to regenerate `mdm_cmp`/`mdm_mtx`.  A
   cross build cannot execute an aarch64 target binary, and letting the recipe
   behave differently on the cross host and on the OHOS worker would be worse
   than not using `install` at all.  `package()` therefore copies the
   executables, tables, databases, manuals and licences explicitly.

### Toolchain

Cross build from WSL (native ext4, `/root/...`; nothing was built under `/mnt/`):

```
conan create . \
  -pr:h=ohos-aarch64-lkyz \
  -pr:b=ohos-aarch64-wsl-xbuild-linux \
  --build=missing --build="spaln/*"
```

Conan 2.29.1 (OHOS-adapted), clang 15 targeting `aarch64-linux-ohos`, sysroot
from the OHOS SDK.  Compiler / archiver come from
`tools.build:compiler_executables` (R33); no bare `${CC}`/`${CFLAGS}` is used.

## 4. `makmdm` and the parameter tables — honest record

`makmdm` does **not** read the table directory: it builds a PAM matrix from
hard-coded constants and writes `mdm_cmp` (20 doubles, the background amino-acid
composition) and `mdm_mtx` (74 896 bytes).  It is deterministic — two
consecutive runs produce byte-identical files.

A local host build (`g++ -O2`) of the very same `makmdm.cc` was compared with
the tables shipped inside the `ver.3.0.7` archive:

* `mdm_cmp` — **byte-identical** (sha256 `a1473e8f402aaf34fc561143c11b2ba7…`).
* `mdm_mtx` — same size (74 896 bytes) but **9 of 74 896 bytes differ**,
  first divergence at byte offset 11 553.

So the file upstream ships in the release archive was produced by a slightly
different floating-point environment than a fresh build of the same source.
The recipe ships the release-archive tables verbatim because (a) they are the
values upstream releases, and (b) regenerating them at package time would make
the package depend on the build host's floating-point behaviour and could not
be reproduced by the packaged `makmdm` itself.  `test_package` covers this:
assertion 9 requires the regenerated `mdm_cmp` to match the packaged one
numerically (|Δ| ≤ 1e-9, the exact bit pattern is compiler dependent), and
assertion 10 requires the regenerated `mdm_mtx` to have the same geometry.

**Follow-up for a human:** if the maintainers prefer the install-time
regeneration, the change is to run `makmdm` on an aarch64/OHOS worker once and
commit the resulting `mdm_mtx`, or to accept `make install` semantics only in
the target-native CI job.

## 5. Runtime data layout

`configure` was called with

```
--exec_prefix=<package>/bin
--table_dir=<package>/share/spaln/table
--alndbs_dir=<package>/share/spaln/seqdb
```

so the binaries look for their parameter files in the package itself.
`Ftable::getpath` searches `.`, then `$ALN_TAB`, then the baked-in path;
`package_info()` therefore also exports `ALN_TAB` through the Conan run
environment, which keeps the package usable if it is relocated.

## 6. Verification

`conan create` result: **success** (10 programs built, table installed, package
created).  The `test_package` consumer was compiled for aarch64 with the OHOS
toolchain by CMake.

`conan create` runs on an x86_64 host, so `test_package` cannot execute its
aarch64 consumer binary there; it prints an explicit deferral message instead of
silently skipping (`build host machine=x86_64: deferring execution of the
cross-compiled OHOS consumer test to the aarch64 worker`).  The same binary was
therefore executed locally under the OHOS guest rootfs as additional evidence:

```
$ /usr/bin/qemu-aarch64 -L /opt/ohos-guest <pkg>/bin/spaln
No input seq file !

*** SPALN_ARM_NEON version 3.0.7 <250522> ***

$ /usr/bin/qemu-aarch64 -L /opt/ohos-guest test_spaln <pkg>/bin/spaln
spaln OHOS consumer assertions: 10/10 passed          # exit code 0
```

The banner reports `_ARM_NEON`, i.e. the aarch64 SIMD path was compiled in
rather than the scalar fallback.  `readelf -d` on the packaged `spaln` reports a
single dynamic dependency, `NEEDED libc.so` — the program is otherwise
self-contained (zlib and libc++ are linked statically by the OHOS driver).

Build-host sanity: every path involved (`/root/ohpcd-work`, `/root/.conan2`,
`/root/wt-spaln`) is on the WSL-native ext4 filesystem; nothing was built
through `/mnt/`.

## 7. Risks / follow-ups

* `table/mdm_mtx` divergence described in §4.
* `ci/config/no_official_test.txt` is deliberately **not** touched by this PR
  (it is outside `archives/s/spaln/3.0.7/`, and this PR is package-atomic); if
  the L1 whitelist is mandatory for packages without upstream tests, a
  maintainer should add `spaln` there in a separate change.
* 8 clang warnings come from upstream code (`char` compared against the
  constant `-2` in `codepot.cc` / `fwd2h1_wip_simd.h`); they are pre-existing
  and were left alone.
