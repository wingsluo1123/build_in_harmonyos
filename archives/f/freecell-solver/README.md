# Freecell Solver

Freecell Solver is Shlomi Fish's C solver for Freecell and similar card
solitaire games. It ships a public C library (`libfreecell-solver.so`,
headers under `include/freecell-solver/`) and a family of command-line
solvers and board helpers. This archive packages version 6.16.0 for
HarmonyOS PC.

- Upstream: https://fc-solve.shlomifish.org/
- Build system: CMake
- License: MIT

## Package contents

- `lib/libfreecell-solver.so` with `lib/pkgconfig/libfreecell-solver.pc`
  and 10 public headers (`fcs_user.h`, `fcs_move.h`, `fcs_enums.h`, ...)
- `bin/`: the `fc-solve` solver plus `freecell-solver-range-parallel-solve`,
  `freecell-solver-fc-pro-range-solve`, `freecell-solver-multi-thread-solve`,
  `dbm-fc-solver`, `depth-dbm-fc-solver`, `pi-make-microsoft-freecell-board`
  and five Python board helpers
- `share/freecell-solver/` preset scripts, `share/man/man6/` manual pages

## HarmonyOS configuration

The upstream CMake project lives in the `fc-solve/source` directory of the
release tarball, so the recipe configures and builds from there. The tarball
does not bundle the rinutils headers its CMake bootstrap looks for; the
recipe stages rinutils 0.6.0 at `fc-solve/source/rinutils`, the exact path
`cmake/rinutils_bootstrap.cmake` includes, and patch 0007 removes the
`git submodule update --init` branch, which cannot run on an extracted
tarball.

The OHOS perl distribution has no CPAN. The three generators that needed Moo
or Template Toolkit are rewritten in plain Perl (patches 0003-0005), and the
`Path::Tiny` dependency is satisfied by the `libpath-tiny-perl/0.118` tool
requirement through `PERL5LIB`. The upstream Perl test harness and the
perl-generated `.t` scripts stay disabled through the new
`FCS_SKIP_PERL_TEST_HARNESS` / `FCS_SKIP_PERL_GENERATED_TESTS` switches,
while the five upstream cmocka C test programs are registered with CTest
directly (patch 0002, no test-code changes). cmocka is consumed through
`FIND_PACKAGE(cmocka CONFIG)` because OHOS provides no pkg-config entry for
it.

On OHOS the recipe supplies a build-folder-only `Platform/HarmonyOS.cmake`
that includes CMake's Linux platform rules, and emits a single unversioned
`libfreecell-solver.so` with a bare `DT_SONAME`
(`CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`) because HarmonyOS user storage
does not support CMake's versioned symlink chain. `DISABLE_APPLYING_RPATH=ON`
keeps the conan cache prefix out of the binaries and a `$ORIGIN`-based
install RPATH lets the installed CLI tools find the library in place. After
`cmake install()` rewrites RUNPATH (which invalidates the OHOS
`.codesign` section), `package()` re-signs every packaged ELF.

## Dependencies

- Build tools: gperf/3.3 (configure-time hard requirement),
  libpath-tiny-perl/0.118 (Perl generators)
- Test only: cmocka/2.0.2
- No runtime library dependencies beyond libc/libm

## Validation

`conan create` on HarmonyOS/aarch64 runs the five upstream CTest programs
(5/5 passed) and the consumer package (13/13 API checks plus 3/3
installed-package contract checks). `conan-verify` reports Verdict PASS.
