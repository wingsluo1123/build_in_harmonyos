# DRAFT-pd-purepd-0.1.1-abstraction-headless-load

> Contributor: PDPUREPD | Status: DRAFT | Updated: 2026-10-17
> Source: pd-purepd 0.1.1 OHOS adaptation (26 abstractions, no C source, no build step)

## Symptom

A Pd library that ships **only abstractions** cannot be adapted with the usual
Conan recipe shape:

```text
$ make                          # upstream Pd library template, SOURCES is empty
make: Nothing to be done for 'all'.
$ make check
make: *** No rule to make target 'check'.  Stop.
```

and it has no self-proving artifact either: the payload is data that only a Pd
interpreter can load. Run naively, `pd patch.pd` starts the GUI/audio main loop
and never returns in a headless job; run without a closed search path, Pd can
resolve a name from its own installation, so a green test says nothing about
the package.

This is the abstraction-side counterpart of
`DRAFT-pd-external-headless-host-load-verification` (pd-maxlib/pd-mjlib), which
covers C plugins that the host `dlopen()`s. Here there is no `.pd_linux`, no
plugin API, no shim - just `.pd` files and the interpreter's search path.

## Root cause

Three independent properties of the ecosystem have to be handled together:

1. **No compile step.** The upstream Makefile keeps the Pd template's
   `SOURCES` list empty and defines no test target, so `build()` has nothing to
   do and `make check` does not exist. Following the Makefile recipe template
   produces a meaningless step plus a host `make` dependency.
2. **The verifier is an interactive program.** Pd's main loop only ends on an
   explicit quit, a GUI disconnect or a signal; `-batch` is the switch that
   removes GUI, real-time, audio and MIDI and runs the scheduler off-line.
3. **The search path decides what is being tested.** Pd resolves object names
   through its standard paths (`extra/`, the patch directory, the current
   directory) before falling back to anything else, so without `-nostdpath`
   plus an explicit `-path <package libdir>` the test cannot distinguish the
   package from the interpreter installation.

`puredata/0.56.5` is published with an OHOS binary that matches the CI profile
(`os=OHOS os.version=6.0 arch=armv8 compiler=clang 15 libc++ cppstd 17
Release`), so the interpreter can be a test-only dependency and costs no source
build.

## Fix

```sh
pd -batch -nogui -noaudio -noprefs -nostdpath \
   -path <pkg>/lib/pd-externals/<library> \
   -open <patch> -send "; pd quit"
```

1. **Layout.** Reproduce upstream's own install layout with `copy()`:
   `objectsdir = $(prefix)/lib/pd-externals` plus `LIBRARY_NAME` gives
   `<pkg>/lib/pd-externals/<library>/`, the same place the other pd-* packages
   of this repository use, and a real `lib/` artifact for the L5 check. Do not
   reproduce that layout through `make libdir_install`: the install target
   re-links, falls back to the host compiler and needs a host `make`/`install`
   (the pd-chaos adaptation hit exactly that with
   `Relocations in generic ELF (EM: 183)`).
2. **No `build()`.** There is nothing to compile and no upstream test to run;
   record `upstream_test_in_build: false` and the real consumer-test assertion
   count in `test_package/MANIFEST.yml` instead of inventing a check.
3. **Test-only interpreter.** `puredata` belongs in `test_package`, not in the
   library recipe: the library is architecture-independent data and must stay
   installable without the whole Pd application (whose `validate()` also
   restricts it to Linux/OHOS). Take the binary from the dependency's package
   folder by absolute path - a bare `pd` is not guaranteed on `PATH`.
4. **Termination.** `-send "; pd quit"` is a command-line message evaluated by
   `sys_main()` *after* all `-open` patches finished loading, and loadbangs run
   synchronously inside `glob_evalfile()`; every patch action has therefore
   happened before the quit. This is not the racing pattern that
   `DRAFT-pd-external-headless-host-load-verification` forbids (`; pd quit;`
   *inside* the patch, where the quit competes with loadbang prints); it does
   not match that entry's forbid pattern. Keep a subprocess timeout (60 s) as a
   second safety net so a stuck interpreter fails loudly.
5. **Layered assertions.** The data layer (file inventory, Pd patch structure,
   `#X connect` index ranges, class resolution limited to Pd vanilla plus the
   shipped abstractions) runs everywhere and needs no interpreter; the runtime
   layer needs the real `pd`; the negative control is described in
   `DRAFT-pd-purepd-0.1.1-host-builtin-name-shadowing`.

## Scope boundary

This entry covers the packaging and invocation contract for abstraction-only Pd
libraries. C plugins (`.pd_linux`, dlopen, symbol shims) stay with
`DRAFT-pd-external-headless-host-load-verification`; the general data-package
gating pattern stays with E241/E255.

## Validation

pd-purepd 0.1.1:

- 26 abstractions instantiated in one headless run, 14 deterministic results
  reproduced, exit 0, output on stderr;
- re-verified locally against a Pd 0.56-5 interpreter built from the same
  upstream tag that `puredata/0.56.5` packages: 82 assertions, 0 failures
  (60 data + 22 runtime, including the negative control);
- `conan create . --build=missing` on the host passes the consumer test;
- with the CI OHOS profile the graph resolves `puredata/0.56.5` to a published
  binary (no source build), and the expected single-package CI outcome is L0
  pass, L1 pass, L2 skip (no executable), L4 pass (no patches), L5 pass
  (`lib/pd-externals/purepd` has content).
