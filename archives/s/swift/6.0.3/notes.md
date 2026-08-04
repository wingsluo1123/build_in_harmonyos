# Swift 6.0.3 HarmonyOS Toolchain Notes

## Scope

This directory tracks the separate Swift toolchain adaptation required by
SwiftPM packages such as `unxip/3.3`. It is intentionally split out from the
`unxip` PR because the package recipe should not hide a missing language
toolchain.

Target host/runtime triple:

```text
aarch64-unknown-linux-ohos
```

## Current Status

The official Swift 6.0.3 Ubuntu aarch64 toolchain was ruled out for direct
HarmonyOS use: after link flattening and signing, the binaries still request
the Linux/glibc interpreter `/lib/ld-linux-aarch64.so.1` and glibc-family
runtime libraries. A minimal glibc loader bundle could start the loader, but
loader-mediated execution of signed Ubuntu/glibc binaries failed with
`failed to map segment from shared object`.

The source-build path has advanced much further. On the true device, the
OHOS-native Swift 6.0.3 probe produced runnable `swift`, `swiftc`, and
`swift-frontend` binaries, built the OHOS/aarch64 stdlib/runtime, staged
Foundation/FoundationXML and Dispatch, and built SwiftPM entrypoints.

As of 2026-08-04, the reviewable stage at
`/storage/Users/currentUser/ohos-users/codex-a/swift-6.0.3-recipe-20260803-040827/swift-ohos-stage-20260804-1042`
is usable from `PATH` for downstream Swift builds. The stage carries the Swift
frontend/driver tools plus the OHOS clang, `ld.lld`, `llc`, `opt`, clang
resource directory, `lib/aarch64-linux-ohos` runtime bits, and the runtime
libraries needed by the staged Swift/SwiftPM executables. With
`OHOS_SYSROOT/OHOS_SDKROOT/SDKROOT` pointing at the true-device sysroot and the
stage library paths in `LD_LIBRARY_PATH`, `swift --version`, non-optimized
`swiftc hello.swift -o hello`, and optimized `swiftc -O hello.swift -o
hello-opt` all pass through the packaged Conan `test_package`.

Most importantly, the toolchain path built a real downstream SwiftPM package:

```text
unxip/3.3@ohpcd/stable
```

True-device evidence:

```text
$BASE/logs/conan-create-unxip-swiftpm-irhandoff-20260803-004816.out
$BASE/logs/conan-test-unxip-swiftpm-irhandoff-20260803-0104-test.out
$BASE/logs/conan-create-unxip-swiftpm-irhandoff-20260803-0105-full-create.out
```

Observed result:

```text
Build complete! (456.70s)
unxip 3.3
TEST_RC=0
CREATE_RC=0
```

## Patch Areas

The reviewable patch set must cover these areas:

1. Swift core build support and stdlib CMake:
   add `OHOS` as an SDK, map `ohos-aarch64` to
   `aarch64-unknown-linux-ohos`, reuse Linux/POSIX stdlib sources, and avoid
   separate `pthread`, `dl`, and `m` linkage because OHOS resolves those
   through libc.
2. Swift frontend/platform logic:
   map `linux-ohos` resources to `lib/swift/ohos` and expose `os(OHOS)` while
   preserving Linux-compatible source conditions where needed.
3. SwiftDriver and SwiftPM:
   parse `ohos` as the Linux environment, propagate SDK/sysroot/resource-dir
   defaults, disable or avoid unsupported index-store paths, select the OHOS
   clang/linker path, add `--code-sign`, and keep package loading compatible
   with `uname -s = HarmonyOS`.
4. ClangImporter/PCM handling:
   avoid the object PCH container path for OHOS and use raw PCM behavior,
   because the OHOS LLVM 15 fork could serialize the AST but trapped while
   wrapping the module into an object container.
5. Optimized object emission:
   formalize the IR handoff currently proven by the experimental wrapper:
   `swift-frontend -emit-ir`, optional metadata cleanup through `opt`, object
   emission through OHOS `clang-15`, and signing of produced ELF files.
6. Runtime staging:
   stage Swift stdlib, Foundation, FoundationXML, Dispatch, libxml2, xz, and
   zlib library paths without hard-coded probe directories.

## Local Assets

The local initial platform patch was generated from:

```text
local Swift OHOS probe workspace: swift-ohos-patched-files-20260727-1005.list
local normalized draft: swift-initial-ohos-platform.patch
```

`patches/0001-add-ohos-platform-sdk-and-swiftpm-triple.patch` now carries the
platform/SDK/triple work in normalized relative-path form. It intentionally
does not include the early diagnostic instrumentation from the ClangImporter
experiments.

`patches/0002-ohos-driver-swiftpm-runtime-irhandoff.patch` carries the later
true-device changes needed for the downstream package build:

- SwiftDriver default SDK/sysroot/resource-dir propagation for `linux-ohos`
  targets.
- OHOS linker selection through `clang-15`, `--sysroot`, LLD, and
  `-Wl,--code-sign`.
- SwiftScan `RTLD_DEEPBIND` compatibility on OHOS.
- SwiftPM Basics compatibility for HarmonyOS process, file-system, environment,
  and URLSession gaps observed during native SwiftPM bring-up.
- Foundation XML/networking toggles and the CoreFoundation
  `posix_spawn_file_actions_addchdir_np` fallback.
- ClangImporter raw PCM behavior for OHOS module builds.

`scripts/swift-irhandoff-wrapper.c` records the source form of the experimental
optimized object handoff wrapper. It deliberately avoids signed ELF binaries and
probe-machine absolute paths; real compiler, clang, opt, sysroot, resource-dir,
and Swift arch module paths are expected from environment variables or the
packaged toolchain layout.
The staged toolchain installs this wrapper as both `swiftc` and
`swift-frontend`, while preserving the real binaries as
`*.real-irhandoff.real`. The wrapper now resolves `PATH` invocation back to the
absolute stage binary, injects the OHOS SDK/resource/tool defaults for driver
jobs, and prefers sibling `llc`/`opt` from the stage before falling back to
environment variables.

## Review Follow-up

The 2026-08-03 AI review P0/P2/P3 items were folded back into the staged patch
set:

- Removed the dangling empty `if` block in the ClangImporter CC1 argument
  filter.
- Removed the C-side `__OHOS__` conditionals from the exported patches where
  OHOS can reuse the Linux or non-glibc fallback paths. The remaining Swift
  `os(OHOS)` conditionals are tied to Swift platform/triple identity and
  sigaction/loader layout and remain a path C review boundary.
- Preserved the SwiftPM file-lock `blocking` parameter instead of silently
  dropping it.
- Freed `allocated_real` on the IR handoff wrapper sysroot error path.
- Switched `monitor-device.sh` to a PID-qualified process snapshot file.
- Added the software-level `archives/s/swift/commands.json` metadata.
- Replaced the mutable OHOS LLVM branch tarball source entry with a pinned
  commit reference for `2026_0313_llvm15_release`.
- Initialized the IR handoff wrapper cleanup pointer before all `goto cleanup`
  paths, and made the non-intercept pass-through path use `execvp` when the
  selected real tool has no slash.
- Corrected the SwiftDriver loader condition to `!os(OHOS)`.
- Made SwiftPM blocking locks, nonblocking locks, and `prepareLock` derive the
  same lock file name from the full path string instead of only `basename`,
  avoiding cross-directory collisions and mixed lock identities.
- Enabled `pipefail` in `assemble-stage-ohos.sh` when the device shell supports
  it.
- Tightened stage assembly and `test_package` after true-device smoke testing:
  the packaged stage now requires `swift-frontend` and
  `swift-autolink-extract`, and the smoke compile runs with a writable
  `TMPDIR` plus `SDKROOT`/`OHOS_SYSROOT`/`OHOS_SDKROOT` when a sysroot is
  detectable.
- Addressed the follow-up R19/source-bootstrap review boundary by making the
  Conan default path download the official Swift 6.0.3 component tarballs,
  apply the exported patches, and invoke `scripts/source-bootstrap-ohos.sh`.
  The helper now drives cmark, Swift compiler/stdlib targets, SwiftPM
  `Utilities/bootstrap install`, and stage assembly from a Conan build
  directory.
  Reusing an already assembled stage now requires the explicit
  `SWIFT_OHOS_ALLOW_STAGED_PACKAGE=1` escape hatch and records
  `CONAN-STAGE-PROVENANCE.json` plus a stage/package identity hash.
- Made `swift-irhandoff-wrapper.c` clean temporary `.ll` files by default; set
  `SWIFT_OHOS_KEEP_IRHANDOFF_TEMPS=1` only when debugging IR handoff failures.
- The ClangImporter index-store wrapper is still a source-bootstrap boundary:
  the current patch preserves upstream index data recording when the Clang API
  is available, but bypasses it on this LLVM 15 fork instead of claiming full
  index-store support. Re-enable it after the OHOS LLVM index action path is
  verified.
- The 2026-08-03 09:09 source-bootstrap retry reached `build()` but failed
  before compiler work because the recipe looked for `scripts/` under the
  copied upstream source tree. The recipe now invokes
  `source-bootstrap-ohos.sh` from `exports_sources`, while keeping
  `SWIFT_OHOS_SOURCE_ROOT` pointed at the patched Swift source tree.
- `test_package` no longer probes a user-home sysroot path by default; it uses
  explicit `SDKROOT`/`OHOS_SYSROOT`/`OHOS_SDKROOT` first, then conventional
  system/toolchain sysroot locations.

## True-device Stage Smoke, 2026-08-03

On the shared HarmonyOS true device, `assemble-stage-ohos.sh` produced:

```text
/storage/Users/currentUser/ohos-users/codex-a/swift-6.0.3-recipe-20260803-040827/swift-ohos-stage-20260803-070326
```

The stage contains `swift`, `swiftc`, `swift-frontend`,
`swift-autolink-extract`, `swift-build`, `swift-package`, and
`swift-serialize-diagnostics`, plus SwiftPM runtime libraries and a minimal
`libtinfo.so.6` compatibility shim. Version smoke passed for the four public
entrypoints. A direct `hello.swift` compile and run passed with:

```sh
export TMPDIR=$RUN/tmp
export SDKROOT=/storage/Users/currentUser/usr/local/sysroot
export OHOS_SYSROOT=$SDKROOT
export OHOS_SDKROOT=$SDKROOT
export PATH=$STAGE/bin:/storage/Users/currentUser/validation/toolchain-bin:/storage/Users/currentUser/usr/local/bin:$PATH
export LD_LIBRARY_PATH=$STAGE/lib:$STAGE/lib/swift/ohos:$LD_LIBRARY_PATH
swiftc hello.swift -o hello
./hello
```

`llvm-objdump -p` shows the staged public binaries depend on OHOS `libc.so`
and staged Swift/SwiftPM `.so` files; their current `RUNPATH` still includes
source-bootstrap absolute build paths. Conan run environments add package
`lib/` and `lib/swift/ohos` to `LD_LIBRARY_PATH`, but RUNPATH relocation is
still a follow-up automation item.

Conan packaging validation then passed on the same true device:

```text
notest log: /storage/Users/currentUser/ohos-users/codex-a/swift-6.0.3-recipe-20260803-040827/logs/conan-create-swift-notest-20260803-070911.log
full log:   /storage/Users/currentUser/ohos-users/codex-a/swift-6.0.3-recipe-20260803-040827/logs/conan-create-swift-full-20260803-071356.log
package:    swift/6.0.3#f3b22d7d2d7865a8012161b9191dfb22:876049f3ae10a4560da345bb02378e03e212bc8c#d531c6f21316ff8eb61024b2f5dd4d92
test:       swift-ohos-smoke
```

At 2026-08-03 09:24 CST, the default source-bootstrap path progressed through
cached tarball unpacking and both OHOS patches, then stopped in the LLVM
resource-header phase because the pinned OHOS LLVM substrate exposes
`clang-resource-headers` but not the optional `clang-features-file` ninja
target. `source-bootstrap-ohos.sh` now probes available LLVM ninja targets
before building resource artifacts and also reports the real command exit code
from logged build steps.

At 2026-08-03 09:36 CST, the next run reached the cmark CMake configure step.
The OHOS compiler wrappers under `validation/toolchain-bin` are executable ELF
wrappers, so invoking them through `/bin/sh <wrapper>` made the shell parse ELF
bytes as a script. The bootstrap script now passes executable wrappers directly
to CMake and only uses `/bin/sh <wrapper>` for non-executable wrapper files.

At 2026-08-03 10:01 CST, source-bootstrap reached the Swift compiler build
proper (`swiftBasic`, around 51/933). The next boundary was a too-small UUID
shim (`uuid_generate_time`, `uuid_unparse_upper`, and `uuid_compare` were
missing) plus Swift 6.0.3 CAS backend fields that are not present in the pinned
OHOS LLVM 15 fork. The shim now exports the libuuid entry points used by
`lib/Basic/UUID.cpp`, and the Swift patch compiles CAS backend object-mode
plumbing only when the LLVM headers expose the newer CAS API.

At 2026-08-03 11:11 CST, source-bootstrap validated the CAS guard by compiling
past `TargetInfo.cpp.o` and then stopped at `AccessRequests.cpp.o`.
`NameLookup.h` used `llvm::ArrayRef(Results)` C++17 class template argument
deduction; with the OHOS LLVM 15 fork this deduced an `ArrayRef` over the whole
`SmallVector` object instead of `LookupResultEntry`. The patch now spells the
element type explicitly as `llvm::ArrayRef<LookupResultEntry>(Results)` for the
inner, outer, and all-results helpers.

At 2026-08-03 11:27 CST, source-bootstrap accepted the `NameLookup.h` hunk and
progressed through `AccessRequests.cpp.o`, then stopped at `Builtins.cpp.o`
around 80/933. The OHOS LLVM 15 fork exposes additional
`llvm::Intrinsic::IITDescriptor` pointer descriptors (`PtrToArgument`,
`PtrToElt`, and `AnyPtrToElt`) that Swift 6.0.3 did not cover in the
`-Werror=switch` build. The patch now handles these descriptors through the
existing RawPointer-oriented `makePointer` path rather than adding a catch-all
default branch.

At 2026-08-03 11:59 CST, source-bootstrap validated the intrinsic descriptor
patch by compiling past `Builtins.cpp.o` and then stopped at `Decl.cpp.o`
around 89/933. Swift 6.0.3 references Clang pointer-authentication APIs
(`clang::PointerAuthQualifier` and `QualType::getPointerAuth()`) that are not
fully present in the pinned OHOS LLVM 15 fork. The compatibility patch now
includes Clang's real `PointerAuthOptions.h` type definition but skips the
`getPointerAuth()` call unless the LLVM headers are version 16 or newer.

At 2026-08-03 12:34 CST, source-bootstrap validated the pointer-auth guard by
compiling past `Decl.cpp.o` and then stopped at `DocComment.cpp.o` around
93/933. This exposed the same LLVM 15 `ArrayRef` class template argument
deduction issue seen in `NameLookup.h`; the patch now spells the `BodyNodes`
and `ParamFields` element types explicitly before passing them to
`MarkupContext::allocateCopy`.

The follow-up 12:45 CST run validated the `DocComment.cpp` fix and progressed
to `RawComment.cpp.o` around 131/933, where another `llvm::ArrayRef(SRCs)` CTAD
site failed against LLVM 15. The patch now uses
`llvm::ArrayRef<SingleRawComment>(SRCs)` for that allocation.

The 13:48 CST source-bootstrap run validated that fix by compiling past
`RawComment.cpp.o`; it then stopped around 134/933 in
`RequirementMachine/ConcreteContraction.cpp`. The OHOS libc++/LLVM 15 stream
operators do not provide an `llvm::raw_ostream << std::optional<Type>`
overload, so the debug trace now prints `*substBaseType` after the existing
presence check instead of streaming the optional wrapper.

The 14:20 CST run validated the `ConcreteContraction.cpp` patch by compiling
past the RequirementMachine files and stopped at `Stmt.cpp.o` around 162/933.
This was another LLVM 15 `ArrayRef` deduction site: `llvm::ArrayRef(tmp)` was
deduced as an array over the `SmallVector<VarDecl *, 4>` object, while
`ASTContext::AllocateTransform<VarDecl *>` needs `VarDecl *` elements. The
patch now spells the element type as `llvm::ArrayRef<VarDecl *>(tmp)`.

The follow-up run validated the `Stmt.cpp` fix and reached
`TypeSubstitution.cpp.o` around 172/933. The same LLVM 15 deduction issue
appeared for `ArrayRef(ActivePackExpansions)`, which produced an array over the
`SmallVector<ActivePackExpansion, 4>` container instead of
`ActivePackExpansion` elements. The patch now creates an explicit
`llvm::ArrayRef<ActivePackExpansion>` before splitting outer and inner pack
expansion slices.

The 2026-08-03 14:59 CST source-bootstrap run validated both AST fixes by
compiling past `[172/933] TypeSubstitution.cpp.o` and linking `libswiftAST.a`.
Follow-up AI review feedback was also triaged: the remaining `isOHOSFamily()`
calls are intentionally tied to the OHOS LLVM fork, so the patch now carries an
inline note at both call sites. The staged tarball fallback in `conanfile.py`
also keeps Python's `filter="data"` fast path and adds explicit path/link/special
file checks for older Python runtimes where `tarfile.extractall(filter=...)` is
not available.

The same run stopped at `[198/933] ClangAdapter.cpp.o`. The failures were
version drift between Swift 6.0.3's expected Clang API surface and the OHOS LLVM
15 fork: OpenCL AVC builtin enum spellings use `Ref` rather than `Reference`,
`SwiftImportPropertyAsAccessorsAttr` is unavailable, and
`QualType::getNullability()` still requires an `ASTContext`. Patch 0002 now
includes `llvm/Config/llvm-config.h` in `ClangAdapter.cpp` and gates those sites
with `LLVM_VERSION_MAJOR` checks.

The 15:33 CST follow-up run compiled past `ClangAdapter.cpp.o` and stopped at
`[200/933] ClangDerivedConformances.cpp.o`. The OHOS LLVM 15
`OverloadCandidateSet::OperatorRewriteInfo` constructor only accepts
`(OverloadedOperatorKind, bool)`, while the Swift 6.0.3 source expects the newer
three-argument form with a `SourceLocation`. Patch 0002 now includes
`llvm-config.h` in `ClangDerivedConformances.cpp` and selects the two-argument
constructor for LLVM versions before 16.

The 15:51 CST run validated `ClangDerivedConformances.cpp.o` and then stopped at
`[202/933] ClangImporter.cpp.o`. The earlier AI review suggestion to use
`getLangOpts().` does not match the current OHOS LLVM 15 fork headers for
`CompilerInvocation::getLangOpts()`, which return a pointer in the failing
paths. Patch 0002 now keeps `->` for `invocation->getLangOpts()` and
`Instance->getInvocation().getLangOpts()` while leaving ASTContext-style
`getLangOpts()` references unchanged.

The 16:09 CST run validated the `ClangImporter.cpp` pointer-form
`getLangOpts()` fix and reached `[203/933] ClangIncludePaths.cpp.o`. That file
compiles Windows include path helpers even for the OHOS build, exposing LLVM 15
API drift: MSVC path helpers still take `llvm::Optional<StringRef>` instead of
`std::optional<StringRef>`, and `findVCToolChainViaSetupConfig()` has no
VCTools-version argument. Patch 0002 now adds a small LLVM < 16 optional
converter and selects the older setup-config signature under the same version
guard.

The 16:32 CST run validated `ClangIncludePaths.cpp.o` and stopped at
`[206/933] ClangModuleDependencyScanner.cpp.o`. The OHOS LLVM 15 tree provides
`DepscanPrefixMapping` through the shim header
`clang/Tooling/DependencyScanning/ScanAndUpdateArgs.h`, but Swift 6.0.3 did not
include that header directly. Patch 0002 now includes it behind `__has_include`,
which keeps standard toolchains that provide the symbol elsewhere unaffected.

The 16:52 CST run validated `ClangModuleDependencyScanner.cpp.o` and exposed the
next ClangImporter compatibility batch at `[209/933] ImportDecl.cpp.o` plus
`[210/933] ImportEnumInfo.cpp.o`. Patch 0002 now guards Clang attributes that
are absent in LLVM 15 (`SwiftImportAsNonGenericAttr`, `SwiftVersionedAttr`),
uses an LLVM-version guard around pointer-auth primitive-copy handling, passes
`ASTContext` to older `QualType::getNullability()` call sites, and makes
`ArrayRef<Decl *>` element types explicit before constructing
`TinyPtrVector<Decl *>` or passing completion-handler member slices.

The 17:13 CST run validated the `[209]/[210]` batch and stopped at
`[212/933] ImportName.cpp.o` plus `[213/933] ImportType.cpp.o`. Patch 0002 now
adds LLVM 15 guards for the remaining `QualType::getNullability(ASTContext)`
call sites in those files, skips Swift-versioned Clang attributes that are not
available in the OHOS LLVM 15 fork, uses the LLVM 15 OpenCL AVC enum spellings
in `ImportType.cpp`, and avoids `AttributedType::getAttr()` when building
against LLVM versions before 16. The local patch was syntax-checked with
`git apply --numstat`, `git diff --check`, and `conan export`.

At 17:38 CST the updated recipe files were synced to the true-device recipe
root and a new low-concurrency source-bootstrap run was started through
`logs/launcher-20260803-173825.log` (launcher pid `43330`). Immediately after
launch, both the FRP SSH path and the direct `10.62.230.12:2222` path stopped
returning usable shell sessions: FRP timed out and the direct SSH service closed
the connection. The run may still be progressing in the background; no result is
claimed until the SSH channel is healthy enough to inspect the latest
`swift-targets-build.log`.

The 18:03 CST rerun validated the `ImportName.cpp`, `ImportType.cpp`, and
`Options.cpp` fixes. It compiled past `[215/933] Options.cpp.o`, linked
`libswiftOption.a`, and stopped at `[227/933] OperandOwnership.cpp.o` while
including `include/swift/SIL/Projection.h`. The new failure is the same LLVM 15
`ArrayRef` deduction gap seen in earlier Swift 6 sources: three accessors were
deduced as arrays over `SmallVector<...>` containers instead of over their
element types. Patch 0002 now spells
`llvm::ArrayRef<unsigned>`, `llvm::ArrayRef<Operand *>`, and
`llvm::ArrayRef<ProjectionTreeNode *>` explicitly in `Projection.h`.

At 2026-08-03 13:40 CST, the latest AI review findings were triaged before
resuming the true-device run. Four mechanical findings were accepted and fixed:
the ClangImporter patch no longer uses `getLangOpts()->` where the LLVM 15
headers expose a reference, the cached-source `unzip()` path no longer passes
Conan-unsupported `strip_root`, the test_package compile environment now quotes
environment-derived values with `shlex.quote()`, and the LLVM static dependency
helper keeps Ninja's archive output target names, normalizing LLVM build
absolute paths to relative targets such as `lib/libLLVMMCJIT.a` instead of
stripping them to bare library names. R8 platform-conditional feedback remains
a separate design/compliance item because the current OHOS Swift platform model
still needs targeted replacement rather than a blind text rewrite.

## True-device Stage Package Smoke, 2026-08-04

The stage assembled from the source-bootstrap investigation was preserved at:

```text
/storage/Users/currentUser/ohos-users/codex-a/swift-6.0.3-recipe-20260803-040827/swift-ohos-stage-20260804-1042
```

True-device probes on 2026-08-04 showed the stage is about 3.7 GiB and contains
the entries required by `conanfile.py`:

```text
bin/swiftc
bin/swift-frontend
bin/swift-autolink-extract
bin/swift-build
bin/swift-package
bin/clang
bin/ld.lld
bin/llc
bin/opt
lib/clang
lib/aarch64-linux-ohos/libunwind.a
lib/libxml2.so.16
lib/swift/ohos/aarch64/libswiftCore.so
```

The explicit staged package path was then replayed through Conan with:

```sh
export SWIFT_OHOS_ALLOW_STAGED_PACKAGE=1
export SWIFT_OHOS_STAGED_ROOT=/storage/Users/currentUser/ohos-users/codex-a/swift-6.0.3-recipe-20260803-040827/swift-ohos-stage-20260804-1042
export SDKROOT=/storage/Users/currentUser/usr/local/sysroot
export OHOS_SYSROOT=$SDKROOT
export OHOS_SDKROOT=$SDKROOT
conan create <swift/6.0.3 recipe root> -pr:h <OHOS profile> -pr:b <OHOS profile>
```

Evidence log:

```text
/storage/Users/currentUser/ohos-users/codex-a/swift-6.0.3-recipe-20260803-040827/conan-create-staged-20260804-1108.log
```

The package was created as:

```text
swift/6.0.3#f3851ae855086513ff797eb00e14d21b:e2902872fbec59e67c6e08c692295c900835da05#875ccae49824a70de322cb6db4c0124c
```

The `test_package` ran `swift --version`, built and executed a normal
`hello.swift`, then built and executed `swiftc -O hello.swift` through the same
stage. Both executables were re-signed when `binary-sign-tool` was available and
printed:

```text
swift-ohos-smoke
```

Remaining known boundary: `swift-driver-new` is intentionally not included in
the default packaged stage. When it is copied in, `swift --version` dispatches
to the new driver and hangs on the true device. The validated path therefore
uses the legacy driver entrypoints for `swift`, `swiftc`, `swift-build`, and
`swift-package`; `SWIFT_OHOS_INCLUDE_DRIVER_NEW=1` is reserved for a separate
SwiftDriver follow-up.

## Next Steps

Do not start another heavy Swift build while other `conan create` jobs are
active on the true device. The staged-package replay is complete; the remaining
heavy validation is to replay the default source-bootstrap path from Conan
without `SWIFT_OHOS_ALLOW_STAGED_PACKAGE=1`, preferably at low concurrency
unless the device is confirmed idle. Before starting:

```sh
date
uptime
free -h
snapshot_dir="${TMPDIR:-${HOME:-/tmp}/tmp}"
snapshot="${snapshot_dir}/codex-ps-swift-check-$$.txt"
mkdir -p "$snapshot_dir" 2>/dev/null || true
ps -ef > "$snapshot"
grep conan "$snapshot"
grep clang "$snapshot"
grep make "$snapshot"
grep ninja "$snapshot"
grep swift "$snapshot"
rm -f "$snapshot"
```

Then continue with a low-concurrency source-bootstrap validation. The default
Conan path no longer consumes a prebuilt stage unless explicitly requested:

```sh
export SWIFT_OHOS_LLVM_BUILD_DIR=$HOME/swift-mainline-ohos-src/build/llvm-host-tools-ohos
export SWIFT_OHOS_SOURCE_TARBALL_DIR=$HOME/swift-mainline-ohos-src/sources
export SWIFT_OHOS_CC=$HOME/validation/toolchain-bin/ohos-clang
export SWIFT_OHOS_CXX=$HOME/validation/toolchain-bin/ohos-clangxx
export TMPDIR=$HOME/swift-mainline-ohos-src/tmp
export SDKROOT=${SDKROOT:-$HOME/usr/local/sysroot}
export OHOS_SYSROOT=$SDKROOT
export OHOS_SDKROOT=$SDKROOT
export SWIFT_OHOS_JOBS=2
conan create archives/s/swift/6.0.3 -pr:h ohos_4_1_armv8 -pr:b default -tf ""
conan create archives/s/swift/6.0.3 -pr:h ohos_4_1_armv8 -pr:b default
```

If a reviewer needs to reproduce the already validated stage packaging fast
path, make that boundary explicit and include the stage identity in the package
ID:

```sh
export SWIFT_OHOS_ALLOW_STAGED_PACKAGE=1
export SWIFT_OHOS_STAGED_ROOT=/path/to/swift-ohos-stage
conan create archives/s/swift/6.0.3 -pr:h ohos_4_1_armv8 -pr:b default
```

`source-bootstrap-ohos.sh` still depends on a pinned OHOS LLVM build substrate
with complete `LLVM_DIR`, `Clang_DIR`, `llvm-tblgen`, `clang-tblgen`, and static
component libraries. That substrate is intentionally explicit rather than hidden
behind the Swift recipe, because it belongs to the OHOS LLVM toolchain layer
and was the original missing-environment boundary for this path C work.

Current stage boundary: `swift-driver-new` is built but not copied into the
default packaged stage. When present, `swift --version` dispatches into the new
driver and hangs on the true device; without it, `swift`, `swiftc`,
`swift-build`, and `swift-package` all complete their version smoke through the
validated legacy driver path. Set `SWIFT_OHOS_INCLUDE_DRIVER_NEW=1` only for
the separate SwiftDriver follow-up investigation.
