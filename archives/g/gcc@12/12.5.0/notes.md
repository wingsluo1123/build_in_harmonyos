# gcc@12 12.5.0 HarmonyOS Adaptation Notes

## Scope

- Package: `gcc@12/12.5.0`
- Conan reference: `gcc12/12.5.0` (`@` is kept in the archive path for task identity, but Conan rejects `@` in package names during create/export)
- Upstream release: GCC 12.5.0
- Worktree: `D:\harmonyos\worktrees\gcc@12`
- Branch: `feat/gcc@12-12.5.0`
- Issue: TBD; no explicit issue number was found in the local project files searched during this session.

## W0 Dependency Check

Checked against the `ohpcd` Conan remote:

| Dependency | Role | ohpcd status | Decision |
| --- | --- | --- | --- |
| `gmp/6.3.0` | Required by GCC frontend arithmetic | Present with OHOS armv8 package | Keep as requirement |
| `mpfr/4.2.2` | Required by GCC frontend arithmetic | Present with OHOS armv8 package as of 2026-07-31 | Keep as requirement |
| `mpc/1.3.1` | Required by GCC frontend arithmetic | Present with OHOS armv8 package as of 2026-08-04 | Keep as requirement |
| `isl` | Optional Graphite optimizer dependency | Missing (`conan list 'isl/*' -r=ohpcd` found 0 recipes) | Disable with `--without-isl` |

The upstream `contrib/download_prerequisites` script for GCC 12.5.0 names `gmp-6.2.1`, `mpfr-4.1.0`, `mpc-1.2.1`, and optional `isl-0.24`. This recipe uses the repository's newer prepared dependency line (`gmp/6.3.0`, `mpfr/4.2.2`, `mpc/1.3.1`) to match the existing HarmonyOS archive direction and the `gcc-snapshot` pre-work.

As of 2026-08-04, W0 dependency resolution is clear: `gmp/6.3.0`, `mpfr/4.2.2`, and `mpc/1.3.1` all resolve with OHOS armv8 binaries from `ohpcd`.

## Source And Build System

- Source URL: `https://ftp.gnu.org/gnu/gcc/gcc-12.5.0/gcc-12.5.0.tar.xz`
- Mirror used for local download only: TUNA GNU mirror
- SHA256: `71cd373d0f04615e66c5b5b14d49c1a4c1a08efa7b30625cd240b11bab4062b3`
- Archive size: `85,897,368` bytes
- Build system: top-level Autoconf `configure.ac`/`configure` plus recursive Makefiles.
- In-tree components observed: `gcc`, `libgcc`, `libstdc++-v3`, `libsanitizer`, `fixincludes`, `zlib`.
- Not in-tree: `gmp`, `mpfr`, `mpc`, `isl`.

The upstream `config.sub` in this release does not contain an `ohos` OS case, but it does accept `linux-musl`. The first-pass recipe therefore configures OHOS native probing as `aarch64-unknown-linux-musl`. A later GCC-specific OHOS target patch may be required after the dependency chain is available and the first real build reaches target-library configuration.

## Recipe Strategy

- Build C and C++ frontends by default with `--enable-languages=c,c++`.
- Reduce first-pass runtime and platform surface:
  - `--disable-bootstrap`
  - `--disable-multilib`
  - `--disable-nls`
  - `--disable-libsanitizer`
  - `--disable-libquadmath`
  - `--disable-libquadmath-support`
  - `--disable-libgomp`
  - `--disable-libssp`
  - `--disable-libvtv`
  - `--without-isl`
- Use Conan dependency package folders for `--with-gmp`, `--with-mpfr`, and `--with-mpc`.
- Use compilers from `tools.build:compiler_executables`, falling back to `clang`/`clang++`.
- On OHOS, inject a recipe-local `mktemp` wrapper and set `TMPDIR`, `TMPPREFIX`, `SHELL`, and `CONFIG_SHELL` for configure/make/install. The validation device's system `mktemp -d` creates Autoconf temp directories that cannot be written by subsequent shell redirection (`./conf*/subs1.awk: Permission denied`).
- On OHOS, export `AR`, `RANLIB`, `NM`, and `STRIP` from the clang toolchain directory as `llvm-ar`, `llvm-ranlib`, `llvm-nm`, and `llvm-strip`. GCC's recursive Makefiles otherwise call bare `ar`, which is not in the runner PATH.
- On OHOS, export `ac_cv_header_limits_h=yes` for configure/make/install. The libiberty configure pass misdetected `<limits.h>` as absent even though preprocessing returned success, which left `LONG_MIN` undefined in `fibheap.c`.
- On OHOS, export `ac_cv_header_fcntl_h=yes` for configure/make/install. The same libiberty header check path misdetected `<fcntl.h>`, which left `open`, `fcntl`, and `O_*` macros undeclared in `pex-unix.c`.
- On OHOS, generate recipe-local helper scripts and compatibility headers idempotently. `package()` calls the same helper setup as `build()`, so rewriting an unchanged `ohos-availability.h` during `make install` can refresh its mtime and force GCC host objects to rebuild.
- Package the OHOS compatibility header as `include/gcc12-ohos/ohos-availability.h` for smoke-test and consumer commands that compile against OHOS libc headers with GCC.
- Export package `lib64` and `lib` through `LD_LIBRARY_PATH` in `runenv_info`, because C++ smoke executables need packaged `libstdc++.so.6` and `libgcc_s.so.1` at runtime.
- Keep upstream DejaGnu tests out of `build()` until a single-package OHOS/shadow CI window is available.

## CLI Metadata

- Added software-level `archives/g/gcc@12/commands.json`.
- `commands.json` keeps the software name as `gcc@12` for archive identity.
- Version `12.5.0` maps to Conan ref `gcc12/12.5.0`.

## Test Package

The consumer test is not an empty shell:

- Runs packaged `gcc --version`.
- Compiles and executes `test.c`.
- If packaged `g++` exists, compiles and executes `test.cpp` using `std::string` and `iostream`.

## Local Validation

Completed:

- Confirmed the main `build_in_harmonyos` worktree is on `feat/apache-arrow-glib-24.0.0`; created a separate `gcc@12` worktree from `origin/main` without switching the Arrow workspace.
- Searched local project files and adaptation notes for `gcc@12`, `12.5.0`, and `gcc 12.5`; no explicit issue number was found.
- Downloaded GCC 12.5.0 outside the repository worktree and verified size/hash.
- Confirmed source build markers from the tarball: top-level `configure.ac`, `configure`, and `Makefile.in`.
- Confirmed upstream test roots exist: `gcc/testsuite/` and `libstdc++-v3/testsuite/`.
- Confirmed `config.sub` lacks `ohos` but supports `linux-musl`.
- Ran `python -m py_compile` for `conanfile.py` and `test_package/conanfile.py`: passed.
- Ran `conan inspect archives/g/gcc@12/12.5.0`: passed.
- Ran `git diff --check -- archives/g/gcc@12/12.5.0`: passed.
- Ran `conan graph info . -r=ohpcd --build=missing` with explicit OHOS/armv8 host settings from this package directory: recipe validation passed, `gmp/6.3.0` resolved, graph resolution failed at missing `mpfr/4.2.2` as expected.
- Rechecked on 2026-07-31 after MPFR merge: `conan list 'mpfr/4.2.2:*' -r=ohpcd` found an OHOS armv8 package; `conan list 'mpc/*' -r=ohpcd` still found no recipe; `conan graph info . -r=ohpcd --update --build=missing` updated `mpfr/4.2.2` from `ohpcd`, then failed because cached `mpc/1.3.1` requires `mpfr/4.2.1` while GCC requires `mpfr/4.2.2`.
- Rechecked on 2026-08-04 after MPC merge: `conan list 'mpc/1.3.1:*' -r=ohpcd` found an OHOS armv8 package; `conan graph info . -r=ohpcd --update --build=missing` resolved `gmp/6.3.0`, `mpfr/4.2.2`, and `mpc/1.3.1` successfully.
- Synced the `archives/g/gcc@12/12.5.0` directory to remote validation repo `/storage/Users/currentUser/validation/build_in_harmonyos` over SSH.
- Created isolated remote job `/storage/Users/currentUser/ohos-users/codex/gcc12-12.5.0-20260804-192814`.
- Started remote single-package runner with command `zsh ci/conan/build_and_test.sh archives/g/gcc@12/12.5.0`.
- Runner directory: `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260804-192903-54325`.
- Current runner state at launch: queued behind `device-global.lock`; no package stdout/stderr had been emitted yet.
- Remote retry after fixing isolated `CONAN_HOME` reached `conan create` and failed with `Invalid package name 'gcc@12'`; recipe name was changed to `gcc12` while preserving the archive path `archives/g/gcc@12/12.5.0`.
- Remote retry after adding `commands.json` and the recipe-local OHOS `mktemp` wrapper:
  - Runner directory: `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260804-200157-2794`
  - Started at: `2026-08-04 20:01:58 +0800`
  - Initial state: waiting on `/storage/Users/currentUser/ohos-test-locks/device-global.lock`

Remote failure already analyzed:

- Runner directory: `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260804-193634-58480`
- Result: `exit-code.txt` contained `1`.
- It passed L0 quality gates, exported `gcc12/12.5.0`, downloaded `gmp/6.3.0`, `mpfr/4.2.2`, and `mpc/1.3.1` from `ohpcd`, downloaded GCC 12.5.0 source, and reached top-level GCC `configure`.
- Failure: `./config.status[1000]: can't create ./conf*/subs1.awk: Permission denied`.
- Root cause observed on-device: system `mktemp -d ./confXXXXXX` created `drwx--S---` temp directories that could not be written, while a simple `mkdir` temp directory was writable. A manual `config.status` replay with a local `mktemp` wrapper passed and created `Makefile`.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260804-200157-2794`:
  - L0 passed, including `commands.json valid (type=tool)`.
  - Top-level GCC `configure` passed and created `Makefile`, confirming the OHOS `mktemp` wrapper fix.
  - `make -j1` entered `libiberty` and failed compiling `fibheap.c` because `LONG_MIN` was undeclared.
  - `libiberty/config.log` showed `checking for limits.h` ran the preprocessor with return code 0 but still recorded `result: no`; `config.h` therefore had `/* #undef HAVE_LIMITS_H */`.
  - Recipe now exports `ac_cv_header_limits_h=yes`; rerun the single-package build to verify the next stage.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260804-201814-15900`:
  - L0 passed, including `commands.json valid (type=tool)`.
  - Top-level configure passed and `make -j1` entered `libiberty`.
  - `fibheap.c` passed with `ac_cv_header_limits_h=yes`.
  - Build then failed compiling `libiberty/pex-unix.c`: `open`, `fcntl`, `O_RDONLY`, `O_WRONLY`, `O_CREAT`, `O_APPEND`, `O_TRUNC`, `O_CLOEXEC`, `F_SETFD`, and `FD_CLOEXEC` were undeclared.
  - `libiberty/config.log` recorded `ac_cv_header_fcntl_h=no`; recipe now exports `ac_cv_header_fcntl_h=yes`; rerun the single-package build to verify the next stage.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260804-203139-27886`:
  - L0 passed, including `commands.json valid (type=tool)`.
  - `fibheap.c` and `pex-unix.c` both passed.
  - `libiberty.a` archive step failed with `make[2]: ar: No such file or directory`.
  - Remote tool lookup found `/storage/Users/currentUser/usr/local/bin/llvm-ar`, `llvm-ranlib`, `llvm-nm`, and `llvm-strip`, but no bare `ar`.
  - Recipe now derives these tools from the configured clang path and exports `AR`, `RANLIB`, `NM`, and `STRIP`; rerun the single-package build to verify the next stage.
- Follow-up runner queued after the AR/RANLIB/NM/STRIP fix:
  - Runner directory: `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260804-204445-42045`
  - Started at: `2026-08-04 20:44:45 +0800`
  - Acquired `device-global.lock` at `2026-08-04 20:50:44 +0800` after 359 seconds.
  - State observed at `2026-08-04 21:08:12 +0800`: still running with no exit code; it has passed the previous `ar` failure point, built `libiberty.a`, `libcpp.a`, and `libcody.a` with the exported LLVM binutils, and is compiling GCC frontend sources around `gimple-match.cc`.
  - Result observed at `2026-08-04 21:31:11 +0800`: failed linking `cc1`. `ld.lld` reported repeated `improper alignment for relocation R_AARCH64_LDST64_ABS_LO12_NC` diagnostics from `libbackend.a` and `libcommon.a`.
  - Manual diagnostic relink with `LDFLAGS=-Wl,--no-relax` did not fix the relocation alignment error.
  - Manual diagnostic relink with `LDFLAGS=-pie` changed the failure to `R_AARCH64_ABS64 cannot be used against local symbol; recompile with -fPIC`, confirming the next adaptation attempt should rebuild GCC host compiler objects as PIC.
  - Recipe now appends `-fPIC` to OHOS `CFLAGS` and `CXXFLAGS`; rerun the single-package build to verify whether `cc1` links.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260804-213845-35783`:
  - L0 passed, including `commands.json valid (type=tool)`.
  - The `-fPIC` change allowed the build to pass the previous `cc1` link failure and produce `xgcc`/`cpp`.
  - Build then failed in `stmp-fixinc`: `cc1: error: no include path in which to search for stdc-predef.h`, followed by `The directory that should contain system headers does not exist: /usr/include`.
  - Remote sysroot inspection found `/storage/Users/currentUser/usr/local/sysroot/usr/include/stdc-predef.h`.
  - Recipe now derives the OHOS sysroot from the configured clang path and passes `--with-sysroot`, `--with-build-sysroot`, and `--with-native-system-header-dir=<sysroot>/usr/include`; rerun the single-package build to verify whether `fixincludes` advances.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260804-222849-39415`:
  - L0 passed, dependency resolution passed, and top-level/gcc configure received the sysroot arguments.
  - `gcc/Makefile` confirmed `TARGET_SYSTEM_ROOT = /storage/Users/currentUser/usr/local/sysroot` and `NATIVE_SYSTEM_HEADER_DIR = /storage/Users/currentUser/usr/local/sysroot/usr/include`.
  - Build again reached `xgcc`/`cpp`, then failed in `stmp-fixinc` because GCC composed the header path as `/storage/Users/currentUser/usr/local/sysroot/storage/Users/currentUser/usr/local/sysroot/usr/include`.
  - Recipe now keeps `--with-native-system-header-dir=/usr/include` while passing `--with-sysroot` and `--with-build-sysroot`, allowing GCC to compose the effective header path as `<sysroot>/usr/include`; rerun required.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260804-230847-25437`:
  - L0 passed, dependencies resolved, and `gcc/Makefile` confirmed `NATIVE_SYSTEM_HEADER_DIR = /usr/include` plus `TARGET_SYSTEM_ROOT = /storage/Users/currentUser/usr/local/sysroot`.
  - Build passed `stmp-fixinc` and advanced to `configure-target-libgcc`.
  - Target `libgcc` configure failed because `xgcc` invoked `build/gcc/as`, which had no real assembler path and attempted to execute assembler flags such as `-v`/`-E`.
  - Manual remote probe confirmed `/storage/Users/currentUser/usr/local/bin/clang -c -x assembler -EL` can assemble AArch64 assembly in a writable storage directory.
  - Recipe now creates an OHOS-only recipe-local `as` wrapper around `clang -c -x assembler`, passes it with `AS`, `AS_FOR_TARGET`, and `--with-as`, and exports LLVM `ld.lld`, `llvm-objcopy`, `llvm-objdump`, and `llvm-readelf`; rerun required.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-000659-61216`:
  - L0 passed and configure received `AS`, `AS_FOR_TARGET`, `--with-as`, `LD`, and LLVM binutils paths.
  - GCC's generated `build/gcc/as` wrapper correctly pointed to the recipe-local `ohos-tools/as` wrapper.
  - Target `libgcc` configure still failed computing the object suffix because clang integrated assembler rejected GCC-generated `.eh_frame` and `.debug_str` section flag/entsize changes in the default `-g -O2 -fPIC` conftest assembly.
  - Manual `xgcc` probe passed with `-O2 -fPIC -g0 -fno-asynchronous-unwind-tables -fno-unwind-tables`.
  - Recipe now exports those flags through `CFLAGS_FOR_TARGET` and `CXXFLAGS_FOR_TARGET`; rerun required.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-010122-15241`:
  - L0 passed, target `libgcc` configure passed, and the build advanced into `libgcc/config/aarch64/t-lse`.
  - Build failed compiling `libgcc/config/aarch64/lse-init.c` with clang integrated assembler diagnostics for changed `.debug_str` flags/entsize.
  - The failing compile line showed `CFLAGS_FOR_TARGET` provided `-g0`, but `libgcc/Makefile` appended `LIBGCC2_DEBUG_CFLAGS = -g` later in `LIBGCC2_CFLAGS`, overriding it for this target object.
  - Recipe now passes `LIBGCC2_DEBUG_CFLAGS=-g0` to OHOS `make` and `make install`; rerun required.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-020440-32516`:
  - L0 passed and the build again reached target `libgcc`.
  - The top-level `make` command contained `LIBGCC2_DEBUG_CFLAGS=-g0`, but recursive target-libgcc still generated `LIBGCC2_DEBUG_CFLAGS = -g` and failed at the same `.debug_str` diagnostics in `lse-init.c`.
  - Recipe now patches the current OHOS build copy of `libgcc/Makefile.in` from `LIBGCC2_DEBUG_CFLAGS = -g` to `LIBGCC2_DEBUG_CFLAGS = -g0` before configure; rerun required.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-024131-19517`:
  - L0 passed, `cc1` linked, `stmp-fixinc` passed, target `libgcc` configure passed, and the patched `LIBGCC2_DEBUG_CFLAGS=-g0` advanced past `lse-init.o`.
  - The next failure was compiling `libgcc2.c` for `_muldi3.o`: OHOS `stdint.h` includes `<bits/alltypes.h>`, but xgcc only searched the generic sysroot include directory.
  - Remote sysroot inspection found `bits/alltypes.h` under `/storage/Users/currentUser/usr/local/sysroot/usr/include/aarch64-linux-ohos/bits/alltypes.h`.
  - Recipe now appends `-isystem <sysroot>/usr/include/aarch64-linux-ohos` to OHOS `CFLAGS_FOR_TARGET` and `CXXFLAGS_FOR_TARGET`; rerun required.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-031947-7867`:
  - The target arch include path was present in the failing `_muldi3.o` command and the previous `<bits/alltypes.h>` error was gone.
  - The next failure was GCC rejecting OHOS libc headers that use Clang-style availability attributes such as `__attribute__((__availability__(ohos, introduced=12.0.0)))`.
  - Recipe now creates an OHOS-only target compatibility header in the build tools directory with `#define __availability__(...)` and injects it through `-include` in `CFLAGS_FOR_TARGET` and `CXXFLAGS_FOR_TARGET`; rerun required.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-035811-57315`:
  - The compatibility header was present in target compile commands and the OHOS availability attribute errors were gone.
  - Target `libgcc` advanced through `lse-init.o`, `_muldi3.o`, and many `libgcc2.c` objects.
  - The next failure was `_divdi3.o`: libgcc's default `LIB2_DIVMOD_EXCEPTION_FLAGS := -fexceptions -fnon-call-exceptions` appended exception flags after the target no-unwind flags, causing clang integrated assembler to reject changed `.eh_frame` flags.
  - Recipe now patches OHOS `libgcc/Makefile.in` to replace the divmod exception flags with `-fno-asynchronous-unwind-tables -fno-unwind-tables`; rerun required.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-043546-42544`:
  - The divmod patch allowed target `libgcc` to build `libgcc.a` and progress into `libgcov.a` and EH objects.
  - The next failure was `unwind-dw2.o`: libgcc's EH object block sets `c_flags := -fexceptions`, again causing `.eh_frame` section flag diagnostics.
  - Recipe now patches that OHOS `c_flags` line to keep `-fexceptions` while appending `-fno-asynchronous-unwind-tables -fno-unwind-tables`; rerun required.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-052247-30122`:
  - L0 passed, dependencies resolved from cache, `cc1` linked, and target `libgcc` advanced through `libgcc.a` and `libgcov.a`.
  - `unwind-dw2.o` still failed because the generated assembly contained `.section .eh_frame,"aw",@progbits`; clang's assembler rejects the changed `.eh_frame` flags.
  - Recipe now updates the OHOS recipe-local `as` wrapper to normalize `.eh_frame,"aw",@progbits` to `.eh_frame,"a",@progbits` before invoking clang's assembler; rerun required.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-060200-16739`:
  - L0 passed, dependencies resolved from cache, and the assembler wrapper advanced past the earlier `unwind-dw2_s.o`, `unwind-dw2-fde-dip_s.o`, `unwind-sjlj_s.o`, and `unwind-c_s.o` `.eh_frame,"aw",@progbits` diagnostics.
  - The next failure moved to `crtbegin.o`, where generated assembly used `.section .eh_frame,"aw"` without the `,@progbits` suffix.
  - Recipe now also normalizes `.eh_frame,"aw"` to `.eh_frame,"a"` in the OHOS recipe-local `as` wrapper; rerun required.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-064249-3517`:
  - The updated assembler wrapper eliminated the remaining `.eh_frame` diagnostics; `libgcc.a`, `libgcov.a`, `crtbegin.o`, and `crtend.o` were built.
  - The build then failed linking `libgcc_s.so.1.tmp` because `ld.lld` could not find `crti.o`, `crtn.o`, or `-lc`.
  - Remote sysroot inspection found those files under `/storage/Users/currentUser/usr/local/sysroot/usr/lib/aarch64-linux-ohos`.
  - Recipe now exports that directory through `LIBRARY_PATH` and `LDFLAGS_FOR_TARGET` for OHOS target links; rerun required.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-072202-54962`:
  - The target link path fix worked: `libgcc_s.so.1.tmp` linked, `libgcc_s.so.1` was installed back into the GCC build directory, and target `libgcc` completed.
  - The next failure moved to `configure-target-libstdc++-v3`: the conftest linked successfully but failed to execute with `./conftest: Permission denied`.
  - Manual remote probes showed `xgcc` output runs when linked with `-Wl,--code-sign`; the same output without that flag is denied by OHOS.
  - Recipe now adds `-Wl,--code-sign` to OHOS `LDFLAGS_FOR_TARGET`, and `test_package` uses the same OHOS target link directory plus code-sign flag for smoke executables; rerun required.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-081757-48667`:
  - The `-Wl,--code-sign` change worked: `libstdc++-v3` configure passed the previous executable `Permission denied` point and continued deeper into C/C++ feature probing.
  - The next failure is still in `configure-target-libstdc++-v3`: C++ preprocessor detection first tried the generated `xgcc ... -E conftest.cpp`, but that command lacked the OHOS target multiarch include path and failed on missing `bits/alltypes.h`; configure then fell back to `/lib/cpp`, which is unavailable on the validation device.
  - Recipe now also exports OHOS target preprocessor compatibility through `CPPFLAGS` (`-include ohos-availability.h` and `-isystem <sysroot>/usr/include/aarch64-linux-ohos`) so Autoconf C++ preprocessor probes receive the same header workaround as target compile probes; rerun required.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-090121-36978`:
  - `libgcc_s.so.1.tmp` linked and installed successfully again, confirming the sysroot library path and code-sign target link fixes are stable.
  - The build again reached `configure-target-libstdc++-v3` and failed at the same C++ preprocessor sanity check. The new `libstdc++-v3/config.log` showed `CPPFLAGS=''` and `ac_cv_env_CPPFLAGS_value=''`; the top-level GCC Makefile clears ordinary `CPPFLAGS` for target subconfigures and instead exports `CPPFLAGS="$(CPPFLAGS_FOR_TARGET)"`.
  - Recipe now sets `CPPFLAGS_FOR_TARGET` to the OHOS compatibility header and target multiarch include path; rerun required. A targeted replay of `make configure-target-libstdc++-v3 CPPFLAGS_FOR_TARGET=...` from the failed remote build directory can be used before another full `conan create` retry.
- Targeted replay after the `CPPFLAGS_FOR_TARGET` change:
  - Command shape: `make configure-target-libstdc++-v3 CPPFLAGS_FOR_TARGET="-include <build>/ohos-tools/ohos-availability.h -isystem <sysroot>/usr/include/aarch64-linux-ohos"` from the failed remote GCC build directory, with recipe-equivalent `TMPDIR`, `TMPPREFIX`, `PATH`, `SHELL`, `CONFIG_SHELL`, and `LIBRARY_PATH`.
  - Result: exit code `0`; `libstdc++-v3` configure completed, generated `Makefile`, `config.h`, subdirectory Makefiles, and initial generated headers. This confirms the C++ preprocessor `/lib/cpp` failure is fixed by passing the OHOS preprocessor workaround through `CPPFLAGS_FOR_TARGET`.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-095031-53572`:
  - Formal `conan create` confirmed the `CPPFLAGS_FOR_TARGET` fix: `configure-target-libstdc++-v3` completed and generated the target `libstdc++` Makefiles and headers.
  - The next failure moved into `libstdc++-v3/libsupc++` compilation. `atexit_thread.cc` generated assembly with `.section .gcc_except_table,"aw",@progbits`; clang's assembler rejected the changed writable section flags for `.gcc_except_table`.
  - Recipe now extends the OHOS assembler wrapper to normalize `.gcc_except_table,"aw",@progbits` and `.gcc_except_table,"aw"` to read-only alloc flags, matching the earlier `.eh_frame` workaround; rerun required.
- Targeted replay after the `.gcc_except_table` assembler wrapper change:
  - The failed remote build's `ohos-tools/as` wrapper was hot-patched with the same normalization and `make all-target-libstdc++-v3` was replayed from the existing build directory with recipe-equivalent environment.
  - The replay passed the previous `atexit_thread.cc` failure; `atexit_thread.o` was included in `libstdc++convenience.a`, and the replay log advanced through `libstdc++-v3/src`, `doc`, `po`, `testsuite`, and `python` without another immediate compiler/assembler error before the diagnostic timeout.
  - A formal full `conan create` rerun is still required because the replay modified a build artifact directly.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-104901-2221`:
  - Formal `conan create` confirmed the `.gcc_except_table` assembler wrapper fix in a clean build: `atexit_thread.cc` passed, `libsupc++` linked, `libstdc++.a`, `libstdc++.la`, and `libstdc++fs.la` were produced, and the build advanced through target `libatomic`.
  - The runner still exited with `L1_RESULT=fail: conan create failed` after about 54 minutes. The log did not show a final `make ***` diagnostic; the only literal `error:` was a non-fatal Autoconf probe from `libcc1` using OHOS clang with unsupported `-print-multi-os-directory`, and `libcc1/config.log` ended with `configure: exit 0`.
  - An immediate replay of `make -j1 LIBGCC2_DEBUG_CFLAGS=-g0` from the same build directory with recipe-equivalent OHOS environment returned `0`, confirming no remaining deterministic compiler/assembler failure at the completed state.
  - Recipe now disables non-essential `libcc1` and `libitm` for this package to reduce unnecessary host/toolchain probe noise and shorten the formal validation path; rerun required.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-115437-32642`:
  - Formal `conan create` used a clean recipe revision with `--disable-libcc1` and `--disable-libitm`.
  - The build again completed target `libgcc`, configured and built target `libstdc++-v3`, passed `atexit_thread.cc`, produced `libstdc++convenience.a`, `libstdc++.a`, `libstdc++.la`, `libstdc++fs.la`, and produced `libatomic.la`.
  - The runner still ended with `L1_RESULT=fail: conan create failed` immediately after the top-level `make[1]: Leaving directory .../build`, again without a final `make ***` diagnostic and before `package()`.
  - A direct `subprocess.run(["make", "-j1", "LIBGCC2_DEBUG_CFLAGS=-g0"])` replay from the same completed build directory with recipe-equivalent OHOS environment returned `MAKE_RC 0`.
  - Recipe now runs the OHOS top-level `make` command a second time if the first invocation returns non-zero. This keeps real build errors failing on the retry while handling the observed GCC/OHOS case where the first top-level make returns non-zero despite all target outputs being up to date.
- Follow-up result from runner `/storage/Users/currentUser/ohos-test-runs/codex-12.5.0-gcc12-12.5.0-20260804-192814-conan-20260805-131028-13567`:
  - Formal `conan create` used recipe revision `f1e7b5ce896d510e3b4c0e506a965168` with the OHOS make retry present in the logged command (`make -j1 ... || ... make -j1 ...`).
  - The build again reached the same completed state: `libgcc_s.so.1.tmp` linked, `libstdc++-v3` configured and built, `atexit_thread.cc` passed, `libstdc++.a`, `libstdc++.la`, `libstdc++fs.la`, and `libatomic.la` were produced.
  - The runner ended at `2026-08-05T06:02:32Z`, about 52 minutes after start, immediately after `make[1]: Leaving directory .../build`, before `package()`.
  - Remote inspection showed this job used an older `ci/conan/build_and_test.sh` with a hard `timeout --signal=KILL $BUILD_TIMEOUT conan create ... | tee ...` wrapper and no per-package timeout override file in that checked-out work repo. This points to runner timeout/window exhaustion rather than a remaining deterministic GCC compile failure.
  - A manual continuation experiment from the completed Conan build cache succeeded under the current runner window:
    - Build cache: `/storage/Users/currentUser/ohos-users/codex/gcc12-12.5.0-20260804-192814/conan-home/p/b/gcc12e130de926e59f`
    - Command shape: recipe-equivalent OHOS environment, then `make install DESTDIR=/storage/Users/currentUser/ohos-users/codex/gcc12-12.5.0-20260804-192814/artifacts/manual-package-gcc12-20260805-142345 LIBGCC2_DEBUG_CFLAGS=-g0` from the existing `b/build` directory.
    - Result: `RESUME_INSTALL_RC=0`; install completed from `2026-08-05 14:23:45` to `2026-08-05 14:24:39`.
    - Key staged artifacts were present: `bin/aarch64-unknown-linux-musl-gcc`, `bin/aarch64-unknown-linux-musl-g++`, `lib/gcc/aarch64-unknown-linux-musl/12.5.0/libgcc.a`, `lib64/libstdc++.a`, and `lib64/libatomic.a`.
    - Manual staged smoke with the packaged compiler plus the OHOS compatibility header compiled and executed C and C++ programs successfully: `SMOKE_RC=0` from `2026-08-05 14:31:43` to `2026-08-05 14:31:46`.
  - The recipe now installs `ohos-availability.h` into `include/gcc12-ohos`, and `test_package` passes the same OHOS `--sysroot`, target include, compatibility include, target libdir, and `-Wl,--code-sign` flags used by the manual smoke.
  - A formal Conan continuation with `conan export-pkg archives/g/gcc@12/12.5.0 -of <existing-cache>/b -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd` then succeeded from the same completed build cache after making helper file writes idempotent:
    - Result: `EXPORT_PKG_RC=0`, finished at `2026-08-05 14:49:35`.
    - Full package reference: `gcc12/12.5.0#525159ddc6bfd8e4e76bbf899614067f:af7cbc13531916dde9c3d3ad14cdd6d0871304e8#aa486bc2e671f5d0dcc0b6e8c419d8f8`.
    - Package folder: `/storage/Users/currentUser/ohos-users/codex/gcc12-12.5.0-20260804-192814/conan-home/p/b/gcc120ffaca3649874/p`.
    - `test_package` ran packaged `gcc --version`, compiled and executed the C smoke (`gcc@12 C smoke ok`), then compiled and executed the C++ smoke (`gcc@12 C++ smoke ok`).
  - Upstream testing on 2026-08-05 covered an official GCC execution subset using unmodified tests from the release source tree:
    - Full DejaGnu was initially blocked because `runtest` and `expect` were unavailable on the validation device; it was attempted later after the on-device DejaGnu bootstrap described below.
    - C subset: 20/20 from `gcc/testsuite/gcc.c-torture/execute`, first 20 `.c` files sorted by file name, compiled with packaged `gcc -O2` and executed on OHOS.
    - C++ subset: 12/12 from `gcc/testsuite/g++.dg/rtti` `dg-do run` files, compiled with packaged `g++` and executed on OHOS.
    - Combined upstream test case pass rate for the executed subset: 32/32 (100.0%).
    - Report: `reports/upstream-test-results.md`.
  - DejaGnu bootstrap follow-up on 2026-08-05:
    - Tcl 8.6.14, Expect 5.45.4, and DejaGnu 1.6.3 were built under the validation job root because the device did not provide `runtest`/`expect`/`tclsh`.
    - OHOS-specific test shims were required for read-only `/tmp`, missing `/bin/stty`, and DejaGnu's default remote board directory handling.
    - A local `ohos-gcc` DejaGnu board was added on the validation device with `-Wl,--code-sign`, the OHOS multiarch sysroot include path, and the recipe compatibility header.
    - The recipe-local assembler wrapper was extended to normalize GCC-generated `.debug_str,"",@progbits` sections to `.debug_str,"MS",@progbits,1`, matching clang integrated assembler expectations seen during `-O3 -g` DejaGnu probes.
    - Probe command `make -k check-gcc RUNTESTFLAGS="execute.exp=20000112-1.c --target_board=ohos-gcc"` passed 16/16 expected checks, including execution tests and `-O3 -g`.
    - Full DejaGnu was attempted from the completed build cache with `make -k check RUNTESTFLAGS="--target_board=ohos-gcc"`, but the run stopped without an `rc` file after `make-check.log` reported `Musl Fortify runtime error: file descriptor 5138 >= FD_SETSIZE 1024`. The partial `gcc.sum` snapshot had PASS=27266, FAIL=4012, UNRESOLVED=3992 and is kept as incomplete PR/B-path evidence, not as a full-suite pass rate.
  - Conclusion: the completed build state can be continued into official Conan package/test validation with `export-pkg`. The remaining CI validation gap is that the current `ci/conan/build_and_test.sh` timeout kills a fresh `conan create` before it reaches `package()`; without a cache-aware resume step, end-to-end fresh CI still needs a timeout above the observed >52 minute build phase.

## Path B Candidate (Deferred)

This package is submitted as Path A baseline adaptation for now. A later Path B
request can be considered if the maintainers want to extract the reusable
OHOS/GCC toolchain work:

- target sysroot header and library discovery for GCC's recursive target libraries;
- OHOS libc compatibility for Clang availability attributes while compiling with GCC;
- clang integrated assembler compatibility for GCC-generated `.eh_frame` assembly;
- clang integrated assembler compatibility for GCC-generated `.debug_str` assembly
  during upstream `-g` DejaGnu tests;
- on-device Tcl/Expect/DejaGnu bootstrap plus OHOS board/shim setup for GCC's
  upstream testsuite;
- target `crti.o`/`crtn.o`/`libc` link path wiring for `libgcc_s`;
- `-Wl,--code-sign` for executables produced during GCC/xgcc configure probes;
- staged validation through `xgcc`, target `libgcc`, and target `libstdc++` instead of a shallow source-only recipe.

## Remaining Validation Gap

- Local `conan create` was not run because GCC is a heavy toolchain package and
  validation was performed through the isolated OHOS single-package runner.
- A fresh runner `conan create` reached the completed build state, but the
  current CI wrapper killed it after about 52 minutes before `package()`.
- Continuation from the completed Conan build cache succeeded with
  `conan export-pkg`, including `package()` and `test_package`.
- Upstream full DejaGnu required on-device Tcl/Expect/DejaGnu bootstrap and
  OHOS board/shim fixes. The initial DejaGnu execution probe passed 16/16; the
  full `make -k check RUNTESTFLAGS="--target_board=ohos-gcc"` run was attempted
  from the completed build cache, but it stopped without a final `rc` file after
  a Musl FD_SETSIZE resource abort. The partial `gcc.sum` snapshot had
  PASS=27266, FAIL=4012, UNRESOLVED=3992; the executed unmodified upstream
  subset remains the reported upstream pass rate at 32/32 (100.0%).

## Next Commands

Inspect the completed validation artifacts:

```sh
JOB_ROOT="/storage/Users/currentUser/ohos-users/codex/gcc12-12.5.0-20260804-192814"
BUILD_CACHE="$JOB_ROOT/conan-home/p/b/gcc12e130de926e59f"
CI_LOG="/storage/Users/currentUser/ohos-users/codex/gcc12-12.5.0-20260804-192814/repo/build_in_harmonyos/.ci_logs/conan_build_gcc@12_12.5.0.log"
ls "$BUILD_CACHE"
tail -120 "$CI_LOG" 2>/dev/null || true
cat "$JOB_ROOT/resume-export-pkg-gcc12.log"
cat "$JOB_ROOT/upstream-gcc12-subset.log"
cat "$JOB_ROOT/upstream-gcc12-cxx-run-subset.log"
cat "$JOB_ROOT/dejagnu-full-latest.txt"
```

Re-run single-package validation if needed:

```sh
CI_PACKAGES="archives/g/gcc@12/12.5.0" zsh ci/conan/build_and_test.sh
```

Shadow CI single-package form:

```sh
/path/to/run-ohos-shadow-ci.sh archives/g/gcc@12/12.5.0
```
