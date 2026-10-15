# Spot

Spot is a C++ library and a set of 16 command-line tools for manipulation of
LTL/PSL formulas and ω-automata: translation (LTL/PSL → TGBA/BA, LTLf → DFA),
simplification, transformations, equivalence/emptiness checks and random
generation of formulas and automata. It is developed at LRDE, EPITA.

## Package contents

- Library: `libspot.so` and the full C++ header tree under `include/spot/`
- 16 command-line tools under `bin/`: `autcross`, `autfilt`, `dstar2tgba`,
  `genaut`, `genltl`, `ltl2tgba`, `ltlcross`, `ltldo`, `ltlf2dfa`, `ltlfilt`,
  `ltlfsynt`, `ltlgrind`, `ltlmix`, `ltlsynt`, `randaut`, `randltl`
- Shared data under `share/`
- License: GPL-3.0-or-later

## Dependencies

- No Conan package dependencies: all third-party components (buddy BDD
  library, `ltdl`, gnulib-style portability helpers) are vendored in the
  upstream tarball and built with it.
- Link dependencies are limited to the OHOS system C/C++ runtime.
- Python/SWIG bindings are disabled (`--disable-python`).

## OpenHarmony adaptation

Five environment layers, with zero changes to upstream test files:

- OHOS denies `execve` of `#!` scripts (`EACCES` → 126): `configure` is invoked
  through an explicit shell, and the upstream `make check` reproduction sets
  `LOG_COMPILER` per directory under `tests/` (a global override would also hit
  `buddy/src` and abort `check-recursive` with 127).
- libtool build-tree wrappers cannot be spawned directly: a two-pass trick
  (build first, then copy `.libs/<name>` back over `<name>`) yields real ELF
  binaries; `LD_LIBRARY_PATH` is set to absolute `.libs` directories.
- Scripts created at runtime (the `fake` translator of the `ltlcross*` tests)
  are handled by an `LD_PRELOAD` shim that rewrites `posix_spawn(p)` calls to
  `/bin/sh <script>` and passes ELF targets through untouched.
- The device default `grep` is toybox, which ignores `LC_ALL=C`; the upstream
  `tests/sanity/style.test` then false-positives on multibyte glyphs. A 5-line
  `execv` wrapper exposes GNU grep 3.12 from a private directory prepended to
  `PATH` for the run.
- hmdfs forbids symlinks and masks permission bits: patch `0001` switches
  libtool to `-avoid-version` (single-file `.so`), patch `0002` routes
  `configure`'s `mktemp` through its `mkdir` fallback. After packaging, all ELF
  files are re-signed with the E077 flow (`llvm-objcopy` strip `.codesign` →
  `binary-sign-tool -selfSign` → restore mode bits).

Verification on the real device: upstream `make check` full suite — 214 cases,
188 pass / 0 fail / 26 skipped (all upstream environment guards);
`test_package` 12/12 (probe executor 6/6 + CLI/ELF executor 6/6). Details in
`2.15.1/notes.md` and `2.15.1/reports/`.

## Usage

```bash
# after conan install spot/2.15.1 and activating the generated environment
ltl2tgba -f 'F a & G b' | autfilt --stats=%s
```

## References

- Homepage and documentation: https://spot.lre.epita.fr/
- Source tarball: see `2.15.1/conandata.yml`
