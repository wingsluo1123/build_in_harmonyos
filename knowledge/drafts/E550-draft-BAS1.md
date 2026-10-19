# E550 — Preserve loader tokens across Conan's CMake command boundary

## Symptom and reusable trigger

A CMake shared library has a correct basename SONAME and adjacent files, yet
its CLI cannot load it. The recipe visibly contains `$ORIGIN`, but the actual
ELF dynamic section contains `[/../lib]`. This is a token-propagation failure,
not evidence that the target loader cannot expand ORIGIN.

## Root cause and repair

`CMakeToolchain.cache_variables` produces configure arguments. With the
observed shell-based invocation, a double-quoted `-DCMAKE_INSTALL_RPATH=...`
argument lets the shell expand the unset ORIGIN environment variable before
CMake consumes it. Use `tc.variables` for the literal token so the value is
written inside `conan_toolchain.cmake`, outside that command-line boundary.
Keep variables required before `project()` as cache arguments; this is not a
blanket instruction to migrate every cache setting.

```python
tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN;$ORIGIN/../lib"
tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
```

Supply missing SONAME/runtime link rules only when the actual CMake platform
lacks them. Identical build/install RPATH avoids rewriting signed OHOS ELF.
Never repair this by editing a signed ELF or by removing functional tests.

## Verification and evidence

Follow the same value through configure argv, toolchain text, CMake cache and
`llvm-readelf -d` of the produced ELF. Verify basename SONAME, a literal loader
token and successful real runtime use, not just library existence. Then run
the installed consumer under the declared dependency environment.

SymPol 0.1.9 shared r11 had a valid SONAME but `RPATH [/../lib]` and failed
loading its own library. Shared r12 corrected only the value's generation
boundary: Conan create RC0, all 28 original CLI regressions and two Boost.Test
cases passed, installed consumer assertions 4/4, complete 12-receipt W3_PASS.
Log SHA256: `de902547f695d50e2eef2769b77eec2b8282821cd071e588c9af436c4d040697`.
The earlier static r10 PASS was not reused for the shared candidate.

## Deduplication and boundaries

E504 and E537 cover signed-ELF install rewrites and SONAME/path-bearing NEEDED
problems. E631-draft-9C41 already distinguishes toolchain values from cache
arguments for platform-rule persistence; E625-draft-LRSL covers Make/shell
dollar escaping. This increment is the Conan-generated configure argument
counterexample: a valid SONAME and correct recipe spelling still produce a
token-stripped ELF. It adds a byte-propagation diagnostic before attributing
failure to loader support. It does not claim a new RPATH mechanism, nor that
all shells, CMake generators or OHOS loaders behave identically.

## Installed workflow verification boundary (2026-10-15 increment)

A linked API assertion cannot alone prove a shipped CLI's own-library lookup,
argument-path handling and complete data transformation. After repairing a
loader-token channel, validate the installed executable, not the build-tree
copy or an executable found by PATH. Use a task-private path containing the
characters relevant to the platform, run a real input-to-output transformation,
and feed the serialized output back into the inverse transformation. Compare
exact semantic results rather than checking only successful process exit.

The SymPol rule12 repair adds one such consumer case: an installed OHOS CLI
turns a square's four vertices into four exact rational halfspaces and back
to the original vertices, through Chinese filenames containing spaces.
Explicitly disabling symmetry reduction makes the oracle all four objects,
not an arbitrary orbit representative. Original four QArray assertions remain
one separate API case. Count cases and assertions separately; do not inflate
the consumer case count by the number of checks. This adds a validation
boundary for installed CLI/shared-library delivery, not a new loader mechanism
or proof of unrelated optional backends.

Fresh native sympol-review-201-20261015-r1 completed both clean Conan builds,
all30 original leaves,2 installed consumer cases (including1 workflow), L1e
negative, full12 receipts and release. Official W3 log SHA256:
`95f0431004587f01ccfcfadddaa1b8ba835628c8bbf5bc5756592fe9bbcccc2d`.
