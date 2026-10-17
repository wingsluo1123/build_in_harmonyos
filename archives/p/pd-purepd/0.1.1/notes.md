# pd-purepd 0.1.1 HarmonyOS adaptation notes

## Scope

- Package path: `archives/p/pd-purepd/0.1.1`
- Branch: `feat/pd-purepd-0.1.1`
- Task type: A (pre-adaptation: W0, source/build-system analysis, recipe and
  test_package preparation, host-side verification, next-step device commands).
- Upstream: purepd 0.1.1, "a library of objects written purely in Pd"
  (26 abstractions). License GPL-2.0-or-later.

## W0 dependency check

`pd-purepd` is a data package: upstream's Makefile has an empty `SOURCES` list,
so the recipe builds nothing and requires nothing.

```sh
conan list "pd-purepd/*" -r=ohpcd        # 0 matches: first adaptation
conan list "puredata/*" -r=ohpcd         # puredata/0.54.1, puredata/0.56.5
conan list "libpd/*" -r=ohpcd            # libpd/0.16.1
conan download "puredata/0.56.5" -r=ohpcd --only-recipe
conan list "puredata/0.56.5:*" -r=ohpcd  # binary exists for the OHOS profile
```

Result:

- No Conan dependency has to be published before this package.
- The only meaningful runtime partner is the Pd interpreter itself.
  `puredata/0.56.5` is already published with a binary for exactly the OHOS
  profile used by CI (`os=OHOS os.version=6.0 arch=armv8 compiler=clang 15
  libc++ cppstd 17 Release`), so `test_package` can load the abstractions in a
  real Pd instead of only inspecting files.
- `puredata` is declared **only** in `test_package/conanfile.py`. Adding it to
  the library recipe would force the whole Pd application on every consumer of
  an architecture-independent data package, and `puredata`'s own `validate()`
  rejects non Linux/OHOS configurations, which would make the package
  unresolvable on hosts that only want the .pd files.
- The requirement is guarded by `if self.settings.os in ("Linux", "OHOS")` so
  that host verification on Windows/macOS (where `puredata` cannot be
  configured) still works.

## Source and build-system analysis

- Source: `purepd-0.1.1.tar.gz` from the official project file area
  (`https://sourceforge.net/projects/pure-data/files/libraries/purepd/`, which
  is also the `Source:` field of Debian's `pd-purepd` copyright file).
  sha256 `a670c612019d2b5715deabd66f914d86db56c92d898b98fb573b0bda94bb9389`.
- The Debian orig tarball (`pd-purepd_0.1.1.orig.tar.gz`) and the Tsinghua
  Debian mirror copy were downloaded as well and hash the same, so all three
  URLs are byte identical; they are listed in `conandata.yml` as download
  fallbacks.
- Tarball content: `Makefile` (Pd library template 1.0.6), `README.txt`,
  `LICENSE.txt`, `purepd-meta.pd`, 26 abstraction patches and 26 matching
  `-help.pd` patches. No C/C++ source at all.
- Build system: the template Makefile with `SOURCES =` empty. `make` has
  nothing to compile (`all:` has no prerequisites), and there is **no**
  `check`/`test` target, so the recipe deliberately has no `build()` step and
  no `make check` call. Adding an empty compile step would only add a host
  `make` dependency.
- `make libdir_install` (not used by the recipe, documented for reference)
  installs to `$(objectsdir)/$(LIBRARY_NAME)` =
  `<prefix>/lib/pd-externals/purepd` with `prefix=/`. The recipe reproduces that
  exact layout with Conan `copy()` so packaging does not depend on a host
  `make`/`install`.

## Packaging decisions

- `package_type = "header-library"` plus `package_id(): self.info.clear()`:
  the content is architecture independent, so one package binary serves every
  profile (the same pattern used by the header-only recipes of this
  repository). No `.so` is produced, so R26 (system library collision) is not
  applicable.
- Layout: `lib/pd-externals/purepd/` (upstream's own `pkglibdir` notion) holds
  the 26 abstractions, their help patches, the meta file, README and LICENSE;
  `licenses/LICENSE.txt` is added as usual.
- `package_info()` exposes `libdirs = ["lib"]` and `resdirs =
  ["lib/pd-externals"]`; `libs` and `includedirs` are empty. A consumer uses
  the resource directory as Pd's search path (`pd -path ...`,
  `libpd_add_to_search_path`). `bindirs` is intentionally not touched: the
  package ships no executable, and the CI L0k check treats any `bindirs` mention
  as a command line tool.
- No `commands.json` (R38 is not applicable: no executable is built).

## Test design (test_package)

`verify_purepd.py` is the only test driver, it has three layers and reports one
combined assertion count:

1. **Data layer (60 assertions, always runs).** The packaged libdir must
   contain exactly the upstream file set; every `.pd` file must parse as a Pd
   patch (root `#N canvas` header, balanced `#N canvas`/`#X restore` blocks,
   every `#X connect` index inside its own canvas); `purepd-meta.pd` must
   declare `NAME purepd` and `VERSION 0.1.1`; and every object class referenced
   by an abstraction must be either a Pd vanilla class or another shipped
   abstraction. That last assertion is the defining property of purepd ("objects
   written purely in Pd"): a new external dependency would fail the test.
2. **Runtime layer (needs `--pd`).** `purepd_instantiate.pd` creates one
   instance of all 26 abstractions and `purepd_smoke.pd` drives the
   deterministic control objects with known inputs. The captured Pd output must
   contain the whole expected result set

   ```
   PUREPD_INV: 0.25      PUREPD_XOR: 5, 0        PUREPD_ALTERNATE_A: 11, 33
   PUREPD_LOG10: 1       PUREPD_DELTA: 3, 7      PUREPD_ALTERNATE_B: 22
   PUREPD_COSH: 1        PUREPD_FIFO: 1          PUREPD_UZI_NUM: 1, 2, 3
   PUREPD_SINH: 0        PUREPD_ONCE: 1          PUREPD_UZI_LAST: bang
   PUREPD_TANH: 0        PUREPD_ONESHOT: bang
   ```
   plus the two loadbang sentinels, and must not contain `couldn't create` or
   `no such object`.
3. **Negative control.** The smoke patch is run a second time *without* the
   package on Pd's search path. It must then report `couldn't create` for the
   abstractions and must not produce any of the expected results. Without this
   layer a green run could be vacuous, and it caught a real weakness during
   development: `[clip]` and `[moses]` also exist as Pd vanilla classes, so
   assertions built on them pass even when the package is missing. Those two
   abstractions are therefore only instantiated (never asserted on values), and
   the smoke patch uses abstractions that only this package provides.

Pd is invoked as

```sh
pd -batch -nogui -noaudio -noprefs -nostdpath [-path <pkg>/lib/pd-externals/purepd] \
   -open <patch> -send "; pd quit"
```

`-batch` runs off-line (no GUI/audio/MIDI), `-nostdpath` keeps the standard
search path out of the test so the abstractions can only come from the package,
`-send "; pd quit"` terminates Pd after the patches were opened - loadbangs run
synchronously inside `-open` (`glob_evalfile()` calls `pd_doloadbang()`), so all
patch work has already happened when the quit message arrives. The validator
also enforces a 60 s subprocess timeout so a stuck Pd fails instead of hanging
the CI job.

## Host-side verification performed

Windows x86_64 host (not the OHOS target); commands and observed results:

```sh
# 1. recipe check: package + data layer of the consumer test
cd archives/p/pd-purepd/0.1.1
conan create . --build=missing
#   -> Sources correctly downloaded from
#      https://downloads.sourceforge.net/project/pure-data/libraries/purepd/purepd-0.1.1.tar.gz
#   -> "purepd checks: 60 assertions, 0 failed"

# 2. runtime + negative control against the same Pd version the OHOS package
#    builds (upstream tag 0.56-5, built locally with MinGW-w64 for this check)
python3 test_package/verify_purepd.py \
  --purepd-dir <pkg>/lib/pd-externals/purepd \
  --patches test_package --pd <pd>/bin/pd
#   -> "purepd checks: 82 assertions, 0 failed"
```

Additional observations from the same local runs:

- All 26 abstractions instantiate in Pd 0.56-5 without an error.
- Repeating the instantiation patch *without* `-path` fails for 24 of the 26
  names (all but `clip` and `moses`, which Pd vanilla shadows), confirming that
  the packaged files are what makes them resolvable.
- `pd -batch -nogui` writes its console output to stderr and exits 0; the test
  reads the combined stream.

## Open risks for the device / shadow CI run

1. **Source download on the worker.** `downloads.sourceforge.net` is used first
   (verified reachable from the host); if the worker cannot reach it, Conan
   falls back to the two Debian URLs, which serve the identical file.
2. **Executing the `puredata` binary.** The test needs the `pd` binary from
   `puredata/0.56.5` to run. If the worker refuses to execute a freshly
   downloaded binary (first-run confirmation), the runtime layer will fail with
   `pd did not terminate`/spawn error while the data layer still passes; the
   captured Pd output is printed by the verifier in that case.
3. **`timeout`/subprocess.** The 60 s bound is implemented in Python, so no
   `timeout(1)` binary is required on the device.
4. **Upstream data quality.** Expectations were captured from the upstream
   release; if a future upstream release changes an abstraction, the smoke
   expectations (and `ABSTRACTIONS`) have to be updated together with the
   version - this is intentional, the test is a regression guard.

## Knowledge contribution (path B: knowledge-base expansion)

The repository already carries related knowledge, and this adaptation was
checked against it before writing anything new:

- 23 `pd-*` packages are adapted (pd-chaos, pd-maxlib, pd-mjlib, pd-zexy,
  pd-smlib, ...). They establish the `lib/pd-externals/<library>/` layout, the
  use of the `puredata` package folder to reach the interpreter, deterministic
  assertions instead of random/time-based classes, and an explicit host binary
  path rather than a bare `pd`. This recipe follows all of it.
- `DRAFT-pd-external-headless-host-load-verification` (pd-maxlib/pd-mjlib)
  covers C plugins that the host `dlopen()`s. Its forbid rule targets
  `; pd quit;` written **inside the patch**, where the quit races with loadbang
  prints. This package does not use that pattern: it passes
  `-send "; pd quit"` on the command line, which `sys_main()` evaluates after
  all `-open` patches have finished loading (loadbangs run synchronously inside
  `glob_evalfile()`), so there is no race. The distinction is spelled out in
  the new draft.
- E241 and E255 cover data/resource packages in general; E241's recipe pattern
  (`settings = None`, no `package_type`, `res/` payload) was considered. This
  recipe keeps declared settings plus `package_type = "header-library"` and
  `package_id()` cleared, because that matches the repository's other
  architecture-independent packages, and it keeps the payload under `lib/` so
  the L5 gate sees a real artifact - the same choice the pd-* family makes.
- The negative-control family (`DRAFT-silent-assertion-artifact-pollution-...`,
  `DRAFT-test-execution-gate-silent-skip-false-pass`, `DRAFT-pytest-9.1.1-...`)
  covers assertions that cannot fail. This adaptation hit a different mechanism
  of the same family and contributed it as a draft.

Two drafts are added under `knowledge/drafts/`:

| Draft | New knowledge |
|-------|---------------|
| `DRAFT-pd-purepd-0.1.1-abstraction-headless-load` | Packaging and headless verification contract for abstraction-only Pd libraries: no `build()`, `lib/pd-externals/<lib>` payload, `puredata` as a test-only dependency, `-batch -nostdpath -path <pkg> -open patch -send "; pd quit"`, and why `-send` differs from the patch-internal quit that the pd-maxlib entry forbids |
| `DRAFT-pd-purepd-0.1.1-host-builtin-name-shadowing` | Host name shadowing makes value assertions vacuous: Pd vanilla already ships `clip` and `moses`, so those assertions passed without the package; the remedy is package-only names plus a search-path negative control, with the collision declared in MANIFEST/notes |

Evidence backing both drafts: 24 of the 26 packaged names fail to resolve
without `-path` (which is how `clip`/`moses` were identified), the negative
control reports 12 `couldn't create` lines and leaks no expected value, and the
final test reports 82 assertions with 0 failures.

## Next steps (single package, in order)

```sh
# on the device / shadow CI worker, only this package
CI_PACKAGES="archives/p/pd-purepd/0.1.1" zsh ci/conan/build_and_test.sh

# shadow CI runner form
/path/to/run-ohos-shadow-ci.sh archives/p/pd-purepd/0.1.1
```

Then check, as usual for a single-package run: `Total: 1`, L0/L1 `pass`,
L2 `skip` (no executable is built), L4 `pass` (no patches), L5 `pass`
(`lib/pd-externals/purepd` is content in `lib/`), and that
`ci-metadata.json` matches the log.
