# DRAFT-spot-2.15.1-libtool-wrapper-exec-make-check-ohos

> Contributor: spot 2.15.1 adaptation (task 10869) | Status: Draft | Updated: 2026-10-04
> Source: archives/s/spot/2.15.1

## Symptom

On an OHOS PC device, an upstream autotools+libtool test suite (`make check`) fails in
three distinct ways before any test logic can run. Exact stderr from the spot 2.15.1
reproduction:

1. `/bin/sh: ./run: No such file or directory` -> `FAIL bddtest (exit status: 127)` —
   `check-recursive` then aborts the whole tree at that subdirectory.
2. `Error relocating /.../bin/genltl: _ZN4spot...: symbol not found` (one line per symbol,
   dozens of lines) -> `FAIL core/bdd.test (exit status: 127)`.
3. `Error loading shared library libbddx.so: (needed by ./bddtest)` -> same relocating
   flood -> `FAIL bddtest (exit status: 127)`.

Same fixed explanation for 2 and 3: the test process cannot load the project libraries.

## Root Cause

Three OHOS constraints stack on top of automake's parallel test harness:

1. **No direct execve of `#!` scripts.** OHOS denies it with EACCES (exit 126) even when
   exec bits are set. The harness directly execs test entries: compiled `check_PROGRAMS`
   are libtool wrapper scripts (real ELF lives in the sibling `.libs/`), and `*.test`
   scripts are normally driven through the project's own `LOG_COMPILER=./run`, itself a
   `#!` script. Upstream `run` internally dispatches by extension (`.test` -> `sh -x`),
   so the only missing piece on OHOS is an explicit interpreter in front of `./run`.

2. **Wrapper replacement loses the wrapper's environment.** Replacing each wrapper in
   place with `cp -f .libs/<name> <name>` is the standard trick, but the removed wrapper
   was what set `LD_LIBRARY_PATH` to the build tree's `.libs` directories. The caller must
   export that variable instead - and **only absolute entries work**: tests execute with
   cwd = their own directory (`tests/core/`, `buddy/src/`, ...), so `LD_LIBRARY_PATH`
   entries that start with `./` resolve against the wrong directory and musl reports
   "Error loading shared library ... / Error relocating ... symbol not found" (exit 127).

3. **`LOG_COMPILER` is per-directory upstream, not global.** spot's `tests/Makefile` sets
   `LOG_COMPILER = ./run`, but `buddy/src/Makefile` has `TESTS = bddtest` with no
   LOG_COMPILER (its test is a compiled program). Forcing
   `make check LOG_COMPILER="/bin/sh ./run"` recursively makes the driver run
   `sh ./run bddtest` inside `buddy/src`, where `./run` does not exist -> exit 127, and
   `check-recursive` kills the run before `tests/` (196 core + 9 sanity cases) is reached.

## Recommended Handling

Two-pass method, purely in the build-tree copy (no upstream test-logic changes):

1. **Pass A (build-only).** `make -jN check TESTS=` — compiles every `check_PROGRAMS`
   without executing any case. Confirms the suite is buildable before touching anything.
2. **Convert wrappers.** For each `.libs/<name>`, if the sibling `<name>` is executable
   and starts with `#!`, `cp -f .libs/<name> <name>`. Idempotent: entries that are
   already ELF are skipped, so reruns convert 0 files.
3. **Absolute library path.** Before any `cd`, compute
   `LIBS=$(find "$BUILD_ABS" -type d -name .libs | tr '\n' ':')` and export
   `LD_LIBRARY_PATH="$LIBS..."`. Use the absolute build directory; relative find output
   (the natural `find . -name .libs` from the build root) is the trap from root cause 2.
4. **Pass B, per directory.** Run `make -k check` separately in each subdirectory that
   declares TESTS: with `LOG_COMPILER="/bin/sh ./run"` where the project ships `./run`
   (spot: `tests/`), and **without** any override where it does not (spot: `buddy/src`,
   whose converted real ELF is directly exec-able). `-k` keeps one failing case from
   hiding the rest.
5. Reference script: `reports/run-upstream-tests.sh <build-dir> [jobs]` (kept with the
   spot package) implements exactly this and writes `check-build.log`, `check-buddy.log`,
   `tests/check.log`.

## Evidence

spot 2.15.1 on the OHOS PC real device (task 10869):

- Round 1 reproduction failed exactly per the three symptoms above (two `./run` 127s plus
  musl relocating floods; logs kept in `reports/upstream-test.out`).
- After the handling above: 188/214 upstream cases pass, 0 fail, 26 skipped (all upstream
  environment guards; tests/ P=187 S=26 + buddy/src P=1 — see `reports/upstream-test-run.md`).
- Consumer-side `test_package` independently exercises the installed package 12/12
  cases (6 C++ probe API cases + 6 CLI/ELF executor cases), and the self-run L2 smoke
  hits 16/16 CLI tools with 20/20 packaged ELFs carrying the `.codesign` section
  (self-run numbers; per-run log files are not kept in the repo).

## Reuse Boundary

Applies to C/C++ autotools+libtool projects with the automake parallel test harness,
executed on OHOS-class devices (script execve denied; musl loader honoring
`LD_LIBRARY_PATH`). Complements - does not replace - the signing-side draft
(`DRAFT-coinutils-upstream-noinst-test-signing`): that one makes *unsigned* check programs
runnable, this one makes the *harness wiring* (driver, wrappers, library path) work. For
scripts created AT RUNTIME and spawned by the test binaries themselves (spot's ltlcross*
`fake` translators), the fix lives one layer below and is covered by the runtime sibling
draft `DRAFT-ohos-script-execve-denied-posix-spawn-shim` (LD_PRELOAD posix_spawn
interposer) - a suite may need both. Does not apply to CMake/Meson suites and does not
turn a host-side run into device evidence. Signing/packaging of check programs that enter
the package is out of scope here.
