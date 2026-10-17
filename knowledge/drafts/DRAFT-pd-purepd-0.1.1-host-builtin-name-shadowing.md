# DRAFT-pd-purepd-0.1.1-host-builtin-name-shadowing

> Contributor: PDPUREPD | Status: DRAFT | Updated: 2026-10-17
> Source: pd-purepd 0.1.1 adaptation (negative control run)

## Symptom

The first version of the pd-purepd smoke patch asserted the results of
`[clip 0 10]` and `[moses 10]`. Both assertions passed - and they also passed
in a run where the package was **not** on Pd's search path at all:

```text
# with -path <pkg>/lib/pd-externals/purepd
PUREPD_CLIP_HIGH: 10
PUREPD_CLIP_LOW: -5
# without -path (package absent) - the same values still appear
PUREPD_CLIP_HIGH: 10
PUREPD_CLIP_LOW: -5
```

The reason is that Pd vanilla already ships classes named `clip` and `moses`;
purepd ships its own implementations of the same names. The assertion therefore
proved something about the interpreter, not about the package.

The CI destructive test (`L1e`) does not catch this either: it moves `bin/`,
`lib/` and `include/` out of the package folder, but a host built-in never
depended on those directories.

## Root cause

An assertion is only evidence if it can fail when the package is missing. Two
conditions break that:

1. **Name shadowing.** The tested name is also provided by the host, the
   interpreter or the toolchain, so it resolves without the package. Besides Pd
   vanilla's `clip`/`moses`, the same class of collision exists for
   system libraries (`zlib`, `ncurses`), pkg-config modules, CMake targets and
   standard-library functions of an interpreted language.
2. **Presence-only checks.** Assertions of the form "this string appeared" (a
   version banner, a `--help` line, a directory listing) hold for a shadowed or
   even empty payload.

Both turn the gate green for a wrong reason, and the CI's `L1e` reverse test
only covers payload files that the test actually links against.

## Fix

1. **Select package-only names for value assertions.** Run the instantiation
   patch once without `-path`; every name that still resolves is shadowed and
   must not carry expected values. For pd-purepd only 24 of the 26 packaged
   names failed to resolve, excluding `clip` and `moses`; the value assertions
   use `inv`, `log10`, `cosh`, `sinh`, `tanh`, `^`, `delta`, `fifo`, `once`,
   `oneshot`, `alternate` and `uzi` instead.
2. **Keep the shadowed artifacts, but only instantiate them.** They are still
   packaged files: they stay in the inventory and structural checks, they just
   do not carry behavioural evidence.
3. **Add a negative control to the test.** The same patch is executed a second
   time with `-nostdpath` and no `-path`; it must report the objects as missing
   and must not leak a single expected value. Both runs are printed to the CI
   log, so the discriminating power of the assertions is auditable.
4. **Write the gap down.** `test_package/MANIFEST.yml` and `notes.md` state
   which names are shadowed, which assertions therefore carry no evidence, and
   which checks replace them. Never count a shadowed assertion as coverage.

## Scope boundary

This entry is about assertion trustworthiness under host name collisions, and
generalises beyond Pd (system libraries, pkg-config/CMake names, interpreter
built-ins). It is the sibling of
`DRAFT-silent-assertion-artifact-pollution-negative-control` (term-shot: an
artifact's own content satisfying the predicate) - same family, different
mechanism. Invocation mechanics for abstraction-only Pd libraries are in
`DRAFT-pd-purepd-0.1.1-abstraction-headless-load`; the general data-package
pattern is E241/E255.

## Validation

pd-purepd 0.1.1, local Pd 0.56-5 (same upstream tag as `puredata/0.56.5`):

- positive run: 14 expected results, 26 abstractions instantiated, 0 creation
  errors;
- negative control: 12 `couldn't create` lines, 0 expected values leaked;
- instantiation-only control: 24 of 26 packaged names fail to resolve without
  `-path`, which is what identified `clip` and `moses` as shadowed;
- final test: 82 assertions, 0 failures.
