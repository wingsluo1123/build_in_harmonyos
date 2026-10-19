# pd-jmmmp 0.61 HarmonyOS adaptation notes

## Scope

- Package path: `archives/p/pd-jmmmp/0.61`
- Branch: `feat/pd-jmmmp-0.61`, task ID 9376 (`feat/pd-jmmmp-0.61` on the task page)
- Task type: A (pre-adaptation: W0 dependency check, source/build-system
  analysis, recipe and test_package preparation, host-side verification, next
  step device / shadow CI commands).
- Upstream: jmmmp 0.61, Joao Pais' Pure Data GUI/utility library - "a
  collection of Pd GUI objects for musical performance". License BSD-3-Clause
  (the `examples/*.png|gif` icons are GPL-2+ from Paul Davis' Ardour, which is
  why the Debian copyright lists them separately).
- Branch/worktree note: the worktree was created with
  `git worktree add --no-checkout ... feat/pd-jmmmp-0.61` plus a cone-mode
  sparse checkout of `archives/p/pd-jmmmp` (the first plain `git worktree add`
  checked out 135342 files and then failed with `Could not reset index file to
  revision 'HEAD'`; the sparse worktree avoids re-checking out the whole
  repository on a Windows host). Commits and PR content are unaffected.

## W0 dependency check

`pd-jmmmp` is a data package: upstream ships no C/C++ source and no Makefile,
so the recipe compiles nothing and has no Conan build dependency.

```sh
conan list "pd-jmmmp/*" -r=ohpcd        # 0 matches: first adaptation of this library
conan list "puredata/*" -r=ohpcd        # puredata/0.54.1, puredata/0.56.5
conan list "libpd/*" -r=ohpcd           # libpd/0.16.1
```

The abstractions reference other Pd libraries (see the runtime map below). W0
status of the ones that have a Conan package in this repository:

| Pd library | Conan package here | published to ohpcd |
|------------|--------------------|--------------------|
| zexy | `pd-zexy/2.4.4` | no (recipe exists in `archives/p/pd-zexy`) |
| iemlib | `pd-iemlib/1.22.3` | no (recipe exists in `archives/p/pd-iemlib`) |
| ggee | `pd-ggee/0.28` | yes |
| maxlib | `pd-maxlib/1.6.0` | yes |
| cyclone, ext13, iemmatrix, list-abs, mrpeach, Gem, ceammc, else, pd-ableton-link | - | no recipe, no package |

Result:

- Nothing has to be published before this package: it has no build dependency
  and its payload does not link against anything.
- **No external Pd library is declared as a Conan requirement.** They are
  runtime prerequisites of a *Pd installation*, in the same sense Debian
  expresses with `Recommends`. Making them hard requirements would (a) block
  the package on the six libraries that have no recipe at all and (b) force
  every consumer of a pure-data package to resolve half a Pd distribution.
- `puredata/0.56.5` is published with a binary for the OHOS profile and is
  used **only** by `test_package` (guarded by
  `if self.settings.os in ("Linux", "OHOS")`, so a host verification on
  Windows/macOS still works). Same decision and same reasoning as pd-purepd.

## Source and build-system analysis

- Upstream 0.61 is distributed through Pd's package manager (deken) as
  `jmmmp-v0.61--externals.zip`; the SourceForge file area that Debian names as
  `Source:` only carries the ancient `jmmmp-0.1.1.tar.gz`, so there is no
  stable upstream tarball URL for 0.61. The Debian source package repacks the
  deken release as `pd-jmmmp_0.61.orig.tar.xz`, and Debian's packaging is the
  authoritative record of the release content
  (`debian/pd-jmmmp.install`: `*.pd`, `*.txt`, `examples/`).
- **Source-choice note (R39/PF7).** The repository's source-URL gate normally
  rejects a Debian repack as the primary source. Here the alternatives are
  worse: SourceForge has no 0.61 artifact at all, and `deken.puredata.info`
  answers programmatic requests with an Anubis proof-of-work challenge (an
  HTML challenge page, not a ZIP), so a CI worker cannot fetch the official
  distribution either. The Debian orig tarball is therefore used and the
  provenance is verified instead of assumed:
  - two Debian mirrors serve the byte-identical file (sha256 below);
  - the Debian binary package `pd-jmmmp_0.61-2_all.deb` ships the same 191
    files under `usr/lib/pd/extra/jmmmp/`: **178 are byte-identical** and 13
    PNGs differ only in the PNG `tIME` timestamp chunk (their `IDAT` pixel
    data hashes are identical; Debian's `dh_strip_nondeterminism` rewrites
    timestamps). So the packaged payload is exactly what Debian ships to Pd
    users, and no file content is invented by the repack.
- Verified byte-identical downloads (sha256 cross-checked):
  - `https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/p/pd-jmmmp/pd-jmmmp_0.61.orig.tar.xz`
  - `https://deb.debian.org/debian/pool/main/p/pd-jmmmp/pd-jmmmp_0.61.orig.tar.xz`
  - sha256 `d7d50ee9d95297735d2fd70fae4d23ac22d3a512ad00627fd9efe9225764e002`, 413952 bytes
  - `mirrors.ustc.edu.cn` lists the file but serves an HTML error page on
    download (877 bytes, different hash), so that mirror is **not** used.
- Tarball content (191 files, top directory `jmmmp/`):
  - 141 `.pd`: 72 abstractions, 68 `-help.pd` patches, 1 `jmmmp-meta.pd`
  - 12 `.txt` data files (`coll.txt`, `jp.menu-audio.txt`, `slider-i.txt`, ...)
    plus `README.txt` and `LICENSE.txt`
  - 38 example images in `examples/` (28 `.png`, 9 `.gif`, 1 `.ppm`) that the
    GUI abstractions display at run time
  - **no** `Makefile`, `configure`, `CMakeLists.txt`, `meson.build` and no C,
    C++ or any other source file
- Build system: none. `build()` is deliberately absent - there is nothing to
  compile and no `make check`/`ctest` to run.
- File encoding: 120 of the 141 patches are Latin-1 (Pd's native byte
  encoding), not UTF-8. The verifier decodes with Latin-1 so byte-faithful
  structure checks work; an UTF-8 reader with `errors="replace"` also works for
  the ASCII keywords but loses the data.
- Two patches (`multiarray.pd`, `jp.garble.pd`) store whole child patches
  inside message boxes, and Pd wraps long records over multiple physical
  lines. A line-oriented parser reports ~280 bogus "malformed connect" errors
  and "101 canvases vs 98 restores" on `multiarray.pd`; the record-oriented
  parser (`records()` in `test_package/verify_jmmmp.py`) rejoins the physical
  lines first and then all 141 files validate cleanly.

## Packaging decisions

- Layout: `lib/pd-externals/jmmmp/` receives the 141 `.pd`, the 12 `.txt` and
  `examples/`, i.e. exactly the Debian `pd-jmmmp.install` set (Debian installs
  the same three groups to `/usr/lib/pd/extra/jmmmp/`). `LICENSE.txt` is also
  copied to `licenses/` as usual.
- `package_type = "header-library"` plus `package_id(): self.info.clear()`:
  the payload is architecture independent, so one package binary serves every
  profile (same pattern as the other data-only recipes here, e.g. pd-purepd).
  No `.so` is produced, so R26 does not apply.
- `package_info()` exposes `libdirs = ["lib"]` and
  `resdirs = ["lib/pd-externals"]`, with empty `libs`/`includedirs` and
  untouched `bindirs` (no executable is shipped, so R38/`commands.json` does
  not apply and L0k must not see a CLI tool).
- No patches. `patches: []` in `conandata.yml` and no `patches/` directory -
  in particular the stale meta file is *not* patched (see below).
- Consumer contract (measured with `pd -batch -nostdpath`, see
  this section and the commands above):
  - `<pkg>/lib/pd-externals/jmmmp` on Pd's search path resolves the flat
    abstraction names (`[scale]`);
  - `<pkg>/lib/pd-externals` additionally resolves the namespaced form that
    some upstream patches use (`[jmmmp/scale]`, `[jmmmp/dsp01]`,
    `[jmmmp/lbang]`, `[jmmmp/metrum]`), because the subdirectory name becomes
    the namespace;
  - `pd -lib jmmmp` alone does **not** load the directory as a libdir in Pd
    0.56.5, so the recipe documents the search-path form rather than a
    `-lib`-only usage.
  This is why `test_package` passes both `-path` entries and why the smoke
  patch uses `[jmmmp/scale ...]` - the namespace form is covered by a real
  assertion.

## Runtime dependency map

Static class analysis of the 72 abstractions (227 distinct object classes):

- 129 classes are Pd vanilla 0.56.5 classes (including the ones that ship in
  `extra/`: `expr`, `expr~`, `fudiparse`, `fudiformat`, `hsl`, `vsl`, ...);
- 75 classes come from other Pd libraries;
- 49 abstractions have a **pure vanilla class closure** and run on a bare Pd;
- 23 abstractions need at least one external library (directly or through
  another shipped abstraction).

The 23, with the classes that require a library:

| Abstraction | External classes |
|-------------|------------------|
| Granulator | cyclone/gate, dbtoa, list-drip, maxlib/pitch, msgfile, rminus, rminus~, selector~, split, splitfilename, tab_sum, uzi |
| LANPdini | else/dir, else/openfile, system.hostname |
| ardourjack-gui | coll, image, l2s, list2symbol, minmax, s2l, shell, unsymbol |
| array-edit | drip, iem_blocksize~, send13, serialize |
| bezier, bezier~ | inv, speedlim |
| dacc~ | iemmatrix, mtx_mul~ |
| dacm~ | zl |
| jp.menu | getdir, l2s, list-drip, list-rot |
| jp.preset | demux, getdir, l2s, list-drip, list-rot, msgfile |
| live2reaper | abl_link~, cyclone/speedlim, mrpeach/packOSC, mrpeach/udpsend, routeOSC, speedlim, splitfilename, udpreceive, unpackOSC |
| matrixctrl | drip, iemmatrix, last-x, list-rev, list-rot, mtx_transpose |
| ml.poly.granulator | 15 `cyclone/*` classes, gate |
| oscD / oscS | oscx/dumpOSC / oscx/sendOSC |
| pix2canvas | gemhead, gemwin, pix_data, pix_draw, pix_image, pix_info |
| rec-name | date, time |
| sliders | listfunnel |
| stoppuhr | (through stoppuhr-clock) |
| stoppuhr-clock | makesymbol |
| swatch | image, list-add, list-apply, list-mult, list-rot |
| swatch-gui | image, list-add, list-apply, list-mult, list-rot, list2symbol, symbol2list |
| uhr | time |

The `[declare]` lines name 14 libraries (`Gem`, `abl_link~`, `ceammc`,
`cyclone`, `ext13`, `ggee`, `iem_tab`, `iemlib`, `iemmatrix`, `jmmmp`,
`list-abs`, `maxlib`, `mrpeach`, `zexy`), but they are not a complete
statement of the prerequisites:

- 4 of the 22 declare nothing at all (`ml.poly.granulator`, `oscD`, `oscS`,
  `stoppuhr-clock`);
- 4 declare only `-lib` (`dacc~`, `pix2canvas`, `rec-name`, `uhr`) and 5 only
  `-path` (`bezier`, `bezier~`, `dacm~`, `sliders`, `swatch`);
- several declarations do not cover the classes the patch actually uses
  (`dacm~` declares `cyclone` but needs `zl`, `bezier` declares
  `cyclone,ggee,maxlib` but needs `inv`/`speedlim`).

For that reason the Debian `Recommends` list - `gem`, `pd-ableton-link`,
`pd-cyclone`, `pd-ext13`, `pd-ggee`, `pd-iemlib`, `pd-iemmatrix`,
`pd-iemutils`, `pd-list-abs`, `pd-maxlib`, `pd-mrpeach`, `pd-zexy` - is
recorded here as the authoritative runtime prerequisite statement, and the
package is documented as "49 abstractions work on vanilla Pd, 23 need one of
those libraries". No `Conan` requirement is derived from it.

## Test design (test_package)

`verify_jmmmp.py` is the only driver and reports one combined assertion count
(173 assertions in the host run below).

1. **Data layer (always).**
   - exact inventory: the packaged libdir must contain the 191 files of
     `jmmmp_inventory.txt` and nothing else;
   - structural validity of all 141 patches: `#N canvas` header, balanced
     `#N canvas`/`#X restore`, every `#X connect` index inside its own canvas,
     after rejoining Pd's wrapped records;
   - the meta file declares `NAME jmmmp`, `LICENSE BSD` and the upstream
     `VERSION 0.48` (see the upstream inconsistency section);
   - complete class dependency map: every class used by an abstraction is Pd
     vanilla, another shipped abstraction (plain or `jmmmp/<name>`) or one of
     the 75 documented external classes; the documented external class list
     and the union of `[declare]` libraries must match the release exactly, so
     a new upstream dependency fails here instead of at run time;
   - the abstractions instantiated by `jmmmp_instantiate.pd` must equal the
     vanilla-closure set computed from the packaged files, which keeps that
     patch a maintained artifact instead of a hand-kept list.
2. **Runtime layer (needs `puredata/0.56.5`).**
   - `jmmmp_instantiate.pd` creates one instance of the 49 vanilla-only
     abstractions and prints `JMMMP_INSTANTIATE_DONE: bang`; no
     `couldn't create`/`no such object` may appear;
   - `jmmmp_smoke.pd` drives nine deterministic abstractions and the captured
     output must match the expected values exactly (see `EXPECTED_SMOKE` in
     the verifier; each expectation is derived from the abstraction source in
     the comment next to it);
   - the same run covers the `jmmmp/scale` namespace form.
3. **Negative control.** Both patches are run again without the package on
   Pd's search path. Every library object must fail to resolve (the expected
   count is computed from the patches themselves: 49 + 9 = 58 failure
   messages), and no expected label/value may appear. Without this layer a
   green run could be vacuous - the class analysis is what makes it cheap, and
   it also catches a future upstream rename that collides with a Pd vanilla
   class.

Pd is invoked as

```sh
pd -batch -nogui -noaudio -noprefs -nostdpath \
   -path <pkg>/lib/pd-externals/jmmmp -path <pkg>/lib/pd-externals \
   -open <patch> -send "; pd quit"
```

`-batch` runs off-line (no GUI/audio/MIDI), `-nostdpath` keeps the standard
search path out so the abstractions can only come from the package, and
`-send "; pd quit"` terminates Pd after every `-open` patch finished loading
(loadbangs run synchronously inside `-open`, so all patch work has happened).
The verifier enforces a 120 s subprocess timeout so a stuck Pd fails instead
of hanging the CI job.

## Host-side verification performed

Windows x86_64 host (not the OHOS target), 2026-10-18:

```sh
# 1. recipe + data layer through Conan
cd archives/p/pd-jmmmp/0.61
conan create . --build=missing
#   -> Sources correctly downloaded from mirrors.tuna.tsinghua.edu.cn (sha256 matches)
#   -> package(): Packaged 141 '.pd', 13 '.txt' (12 data files + LICENSE.txt for
#      licenses/), 9 '.gif', 28 '.png', 1 '.ppm'  => 191 files in the libdir
#   -> "data layer: 191 files, 72 abstractions, 49 vanilla-only,
#       23 external-dependent, 75 external classes"
#   -> "jmmmp checks: 156 assertions, 0 failed"   (EXIT=0)

# 2. full run (data + runtime) against the real Conan package folder, with a
#    locally built Pd 0.56.5 (upstream tag 0.56-5, the source puredata/0.56.5
#    packages; MinGW-w64 build)
python test_package/verify_jmmmp.py \
  --jmmmp-dir <pkg>/lib/pd-externals/jmmmp \
  --patches test_package \
  --pd-externals <pkg>/lib/pd-externals \
  --pd <pd>/bin/pd
#   -> "jmmmp checks: 173 assertions, 0 failed"   (EXIT=0)
```

Evidence collected while designing the test - re-runnable, kept here because
`reports/` is git-ignored repository-wide (`.gitignore:96`) and this package has
no exception:

- 72 abstractions instantiated one by one with `pd -verbose`: 49 clean, 23
  load but report missing classes, 0 missing files;
- the static class closure reproduces exactly the same 49/23 split - the two
  independent methods agree, which is what the "instantiate patch == closure"
  assertion locks in;
- positive run of both patches: 0 creation errors, all 9 label/value sets as
  expected; negative control: exactly 58 creation errors and no leaked value;
- search-path matrix (patch outside the library directory, classes `[scale]`
  and `[jmmmp/scale]`):

  | Pd search path | `[scale]` | `[jmmmp/scale]` |
  |----------------|-----------|-----------------|
  | `-path <pkg>/lib/pd-externals/jmmmp` | resolves | fails |
  | `-path <pkg>/lib/pd-externals` | fails | resolves |
  | both | resolves | resolves |
  | none (negative control) | fails | fails |
  | `-lib jmmmp` only | fails | fails |

- structural parse: the record-oriented reader reports 0 errors over all 141
  patches; a line-oriented reader reports ~280 bogus "malformed connect" lines
  and "101 '#N canvas' vs 98 '#X restore'" on `multiarray.pd`, which stores a
  whole child patch inside a message box;
- encoding census: 120 of 141 patches are Latin-1, 21 pure ASCII.


## Known upstream inconsistencies (documented, not patched)

1. **Stale meta version.** `jmmmp-meta.pd` in the 0.61 tarball declares
   `VERSION 0.48` (and calls itself "a prototype of a libdir meta file"). The
   file is shipped unchanged because it is upstream data and editing it would
   be an undocumented delta from the released tarball; the verifier asserts
   the 0.48 value so a future upstream fix is noticed, and this note records
   why the packaged meta does not say 0.61.
2. **Incomplete `[declare]` lines.** See the runtime dependency map: 4 of the
   22 external-dependent abstractions declare nothing, 9 declare only one of
   `-lib`/`-path`, and some declarations do not cover the classes used.
3. **No `jmmmp/` namespace entry point.** The library relies on being placed in
   a directory named `jmmmp` on Pd's search path; both search-path entries are
   therefore required for the namespaced form (documented in the recipe).

## Device / shadow CI verification (done)

HarmonyOS PC (aarch64, HarmonyOS 6.0, clang 15), single-package isolated run on
2026-10-18:

```sh
# device: isolated worktree of the project clone, our commit applied with git am
cd /storage/Users/currentUser/worktrees/pd-jmmmp-device     # feat/pd-jmmmp-device
sh /storage/Users/currentUser/validation/run-ohos-shadow-ci-local-pdjmmmp.sh \
   archives/p/pd-jmmmp/0.61
```

Result (run `74c30a1c1d5e-20261018T062918Z-46194`):

```
Build Summary:  Total: 1   Success: 1   Failed: 0
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: no patches
L5_RESULT=pass: lib/ has content
```

The consumer test really ran the runtime layer on the device - `puredata/0.56.5`
(package revision `a97a815779545da8139a95c4a7ce8791`) was downloaded from
`ohpcd` and its `bin/pd` was executed:

```
data layer: 191 files, 72 abstractions, 49 vanilla-only, 23 external-dependent,
            75 external classes
jmmmp checks: 173 assertions, 0 failed
```

So the 49 vanilla-only abstractions instantiate in the device Pd, the 9 value
assertions hold on OHOS, the `jmmmp/scale` namespace form resolves, and the
negative control reports its 58 expected creation errors - all with the same
numbers as the host run.

Two harness obstacles were worked around **on the device only** (the repository
and the package are unchanged):

1. **`/tmp` is read-only** (guide #13). The shadow runner builds its compiler
   wrappers with heredocs, so it dies with
   `can't create temporary file /tmp/shXXXX.tmp: Read-only file system` unless
   `TMPDIR`, `TMP`, `TEMP` and `TMPPREFIX` point at a writable directory before
   the runner starts. The launcher sets them to `$HOME/tmp-shadow`.
2. **The runner's hand-written `settings.yml` declares only `os: OHOS, Linux`**,
   and Conan 2 validates the right-hand side of a settings comparison.
   `automake/1.18` (a `tool_requires` of `puredata/0.56.5`) contains
   `if self.settings.os == "Windows":`, which then raises
   `Invalid setting 'Windows' is not a valid 'settings.os' value`. A copy of the
   runner with the full standard `os` list
   (`run-ohos-shadow-ci-local-pdjmmmp.sh`) fixes it; the package itself is
   correct and needs no change. This affects any local shadow run whose
   `test_package` pulls a dependency with such a comparison.

## Open risks that remain after the device run

1. **Source download on the official worker.** Two Debian mirrors are recorded;
   the TUNA mirror served both the host and the device run. If the official
   worker cannot reach either, the source step fails before anything else - it
   is the only network dependency of this package.
2. **`puredata/0.56.5` content drift.** The class lists in the verifier were
   derived from upstream Pd 0.56.5 source and confirmed against the published
   OHOS binary (revision above). A future rebuild of that package with a
   different `extra/` set would surface as a creation error in the instantiate
   layer, not as a silent pass.
3. **Runtime timeouts on a slow device.** 49 abstractions are instantiated in one
   patch; the device run finished well inside the 120 s bound, and a timeout is
   reported with the command line instead of being silently skipped.
4. **Test patch drift.** `jmmmp_instantiate.pd` is checked against the static
   closure, so adding/removing a shipped abstraction without updating the patch
   fails the consumer test by design.
5. **The 23 external-dependent abstractions** are still covered only by the
   static class map (no runtime run), because zexy/iemlib/iemmatrix/cyclone/...
   are not published as Conan packages yet. See the next section.

## Next steps

1. Push `feat/pd-jmmmp-0.61` and open the PR (the device run is green, so the
   `built` state is real and not a host-only claim):

   ```text
   feat(pd-jmmmp): 0.61 适配 HarmonyOS PC
   ```

   PR body: change list (recipe + test_package + inventory + notes), quality
   status (173 assertions, 0 failed on host and on the OHOS device; shadow CI
   `Total: 1 / Success: 1`, L0/L1/L4/L5 pass, L2 skip), and the runtime
   prerequisite table as the "special notes" section.

2. Optional follow-up for full runtime coverage of the 23: adapt and publish the
   missing Pd libraries as separate one-library-per-PR tasks, starting with
   `pd-zexy` and `pd-iemlib` (recipes already exist in this repository, they are
   just not published), then `pd-cyclone`, `pd-iemmatrix`, `pd-list-abs`,
   `pd-mrpeach`, `pd-ext13`, `pd-osc`, `abl_link~`, `else`, and finally the heavy
   `Gem` and `ceammc`. Once the first four are available, extend
   `verify_jmmmp.py` to instantiate the abstractions they unlock and to assert a
   few of their values (roughly 0.5-1 day of work).

## Knowledge contribution (path B)

Two drafts accompany this package (both directly derived from this library's
adaptation, see `knowledge_ref` in `0.61/manifest.yaml`):

| Draft | New knowledge |
|-------|---------------|
| `DRAFT-pd-jmmmp-0.61-pd-patch-record-wrapping` | Pd 补丁以「未转义分号」结束一条 record；折行与消息框内嵌子 patch 会让行式解析器误报（multiarray.pd 实测约 280 条假 connect）；测试补丁的说明文本必须转义 `;` 与 `,`，否则后半句被当成对象执行，打印 `xxx: no such object` 这类与库无关的假错误。 |
| `DRAFT-pd-jmmmp-0.61-shadow-ci-settings-os-windows` | 影子 CI 手写的极简 `settings.yml` 只声明 `os: OHOS, Linux` 时，Conan 2 会校验 settings 比较的右值，`automake/1.18` 的 `if self.settings.os == "Windows"` 直接抛 `Invalid setting 'Windows'`（触发链 puredata → automake，与被适配库无关）；补全 os 列表即可，实测 Total 1 / Success 1。 |

既有知识复用：《适配共性问题与首次真机启动避坑指南》第 13 条（`/tmp` 只读导致
heredoc 失败）在本次真机运行中再次命中（runner 生成 clang wrapper 的 heredoc），
已在 draft 的「附带前置」里记录；`lib/pd-externals` 布局、无头 Pd 加载与负向对照
沿用仓库内既有 `pd-*` 包的做法。