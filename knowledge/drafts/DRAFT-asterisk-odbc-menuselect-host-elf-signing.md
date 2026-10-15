# DRAFT-asterisk-odbc-menuselect-host-elf-signing - Sign a generated Asterisk menuselect host ELF before its first OHOS execution

Asterisk 22.10.1 builds `menuselect/menuselect` and immediately executes it to
produce `menuselect.makeopts`. On HarmonyOS, executable mode alone does not
make that generated ELF runnable: its first execution requires a valid
`.codesign` section. The minimal fix is to sign the generated helper after its
link step and before the make target which executes it.

## Identity and current conclusion

| Field | Value |
|---|---|
| Draft ID | `DRAFT-asterisk-odbc-menuselect-host-elf-signing` |
| Status | Existing verification evidence pending review |
| Suggested destination | Supplement an existing pattern |
| Source PR | [PR #7632](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/7632) |
| Extraction mode | Upgrade of an existing package PR |
| Package | `asterisk-odbc/22.10.1` |
| Upstream source | Asterisk 22.10.1; sha256 `373c98f4d4a1b923b42def0aee03f4e36aca9d1c244a8eeda646da8a97f89663` |
| Source change | `a6ceb013f0db62e01d9281005974ea0776941465` |
| Validated commit | `a23d26ee75b741ca77222245e6ad8625996f9c27` |
| Last updated | 2026-09-10 |

The evidence establishes the timing contract for the Asterisk helper: sign the
ELF before its first `menuselect` execution. It does not establish that every
generated executable, shell script, or target-side binary should be signed by
the same code path.

## Extraction from the existing PR

| Existing PR fact | Location | Reusable mechanism | This draft's addition |
|---|---|---|---|
| CI #36868 could build `menuselect`, but `chmod 755` followed by the first `--check-deps` execution failed with `Permission denied` and make error 126. | Official CI #36868; pre-fix recipe | Build-time generated helpers need a valid OHOS signature before first execution. | Separates first-execution timing from E077's post-install mutation case. |
| `a6ceb013f0` adds `_sign_ohos_executable()` after the `menuselect` build and before `menuselect.makeopts`. | `archives/a/asterisk-odbc/22.10.1/conanfile.py` at `a6ceb013f0` | Copy, remove stale signature, self-sign, restore mode, atomically replace. | Binds the sequence to the make dependency edge that first executes the helper. |
| Official CI #42701 passed on `a23d26ee75`. | Official CI #42701, `OpenHarmonyPCDeveloper-CI-011` | The fixed recipe completed the package pipeline and consumer test. | Historical CI validation only; it does not prove the ongoing full Asterisk test run. |

The original PR contributed the implementation and package consumer test. This
upgrade contributes a bounded Asterisk make-graph case for E318's
first-execution timing, while separating it from E077's post-install mutation
case and ordinary HMDFS shell-script execution handled by E087.

## Trigger, root cause, and minimal repair

The observed failing command sequence in CI #36868 was:

```text
chmod 755 menuselect/menuselect
menuselect/menuselect --check-deps menuselect.makeopts
... menuselect/menuselect: Permission denied
make: *** [Makefile:379: menuselect.makeopts] Error 126
```

The binary is built on the OHOS device and is a generated ELF, not a shell
script. `chmod` restores its executable mode but does not supply `.codesign`.
Signing in `package()` is too late because the make graph consumes the helper
before packaging begins.

The recipe's repair is deliberately local to the generated `menuselect` path:

1. Build `menuselect/menuselect`.
2. Copy it to a same-directory staging file and remove any stale `.codesign`
   section without treating its absence as an error.
3. Use `binary-sign-tool sign -selfSign 1` to write a separate output file.
4. Restore execute bits and atomically replace the original before running
   `make ... menuselect.makeopts`.

Use this only after verifying that the file is a device-executable ELF and
locating its first execution edge. It is not a reason to sign all compiler
outputs by filename or permissions alone.

## Evidence and test accounting

| Evidence | Type | Input and result | Scope and limitation |
|---|---|---|---|
| EVID-01 | Historical target CI | #36868 reached generated-helper execution and failed with error 126 after `chmod`. | Failure baseline; it did not validate the later recipe. |
| EVID-02 | Source change | `a6ceb013f0` inserted `_sign_ohos_executable(menuselect_binary)` immediately after the helper build. | Identifies the repaired dependency edge. |
| EVID-03 | Historical target CI | #42701 passed for `a23d26ee75`, including the package consumer test. | Validates the signing/linker recipe blob at that commit. |
| EVID-05 | Current target package validation | Recipe rrev `a744e096...` completed package build and final `conan test` after the recursive-mutex change. | Validates current package behavior separately from the historical CI record. |
| EVID-04 | Current target execution | The runner registered 599 tests. After excluding 5 protected framework self-tests, 594 ran in 80 clean root categories: 559 PASS, 26 FAIL, 9 NOT RUN. | 125 of the reviewer-provided 724 inventory were not registered by this configuration. |

| Test layer and exact scope | Inventory | Pass | Fail | Skip | Not executed | Basis |
|---|---:|---:|---:|---:|---:|---|
| Upstream Asterisk internal test inventory | 724 | 559 | 26 | 14 | 125 | `559/724` (77.21%); 14 skips are 9 runtime `NOT RUN` results plus 5 protected framework self-tests. |
| Current configured test-runner registration | 599 | 559 | 26 | 14 | 0 | 594 normal entries ran in 80 root categories; 5 protected framework entries did not run. |
| Package consumer probe at validated CI commit | 1 | 1 | 0 | 0 | 0 | Official #42701 package pipeline. |

The rows have different scopes and must not be summed. The `724` upstream
inventory is not represented by the module-only package consumer probe; its
125 unregistered entries are reported as unexecuted rather than inferred to
pass or fail.

## Boundaries and relation to existing knowledge

| Existing item | Existing scope | Delta here |
|---|---|---|
| E318 | Go test compiles a temporary test ELF and immediately executes it. | Asterisk builds a make-graph helper and consumes it during `menuselect.makeopts`; the signature boundary is the same class of first execution but the build edge is different. |
| E077 | Re-signing a mutated installed ELF after `patchelf`, stripping, or object-copy work. | The required signature boundary is before a generated helper's first build-time execution. |
| E087 | HMDFS shell scripts cannot be executed directly in some environments. | `menuselect` is an ELF and `chmod` cannot replace ELF signing. |
| `DRAFT-avr-gcc-bootstrap-generated-host-elf-signing-2245` | Generated host tools in a compiler bootstrap. | A compact Asterisk/Autotools case with a single explicit generated-helper edge. |

Forbidden shortcuts:

- Do not stop at `chmod +x`; it cannot supply `.codesign`.
- Do not defer signing to `package()` or `make install` when the helper runs
  earlier in the build graph.
- Do not blindly sign object files, archives, or target-only ELF files.

## Sources and next action

- Upstream source: `https://github.com/asterisk/asterisk/archive/refs/tags/22.10.1.tar.gz`
- Implementation: `archives/a/asterisk-odbc/22.10.1/conanfile.py` in commit
  `a6ceb013f0db62e01d9281005974ea0776941465`.
- Evidence report: `archives/a/asterisk-odbc/22.10.1/reports/knowledge-evidence.md`.
- CI records: `https://ohpcd.atomgit.com/ci?id=36868` and
  `https://ohpcd.atomgit.com/ci?id=42701`.

The current worktree also contains a recursive-mutex source patch outside this
draft's signing mechanism. It completed a separate target-side package build
and consumer test at recipe rrev `a744e096...`; that result is not used to
expand this draft beyond the generated-helper signing boundary.

Suggested handling: keep this as a supplement to existing generated-host-ELF
signing knowledge pending review. The isolated OHOS result now records its
unregistered source-inventory boundary rather than claiming all 724 tests ran.
