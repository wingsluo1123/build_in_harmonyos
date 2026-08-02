# unxip 3.3 HarmonyOS Preflight Notes

## Scope

- Target library: `unxip`
- Version: `3.3`
- Branch: `feat/unxip-3.3`
- Issue: `#1438` (`https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1438`).
- Source: `https://github.com/saagarjha/unxip/archive/refs/tags/v3.3.tar.gz`
- SHA256: `490c27aeabad33a8c811ada09008d24835f0f701ad40092b450c4788cdf99198`

## W0 Dependency Check

Published in `ohpcd`:

- `libxml2/2.15.3`
- `xz/5.6.2`
- `zlib-ng-compat/2.3.3`

Missing prerequisite:

- Swift 6 toolchain. `Package.swift` declares `swift-tools-version:6.0`; local PATH has no `swift`, `/data/service/hnp/bin/swift` is absent, `conan list "swift/*" -r=ohpcd` found no recipe, and the `cmd-pkgs` README has no Swift entry.

## Source And Build System

- Build system: Swift Package Manager (`Package.swift`) plus a small `Makefile` wrapper.
- Products: CLI executable `unxip`; Swift library target `libunxip`.
- Non-macOS imports: `FoundationXML`, `GNUSource`, `getopt`, `lzma`, and `zlib`.
- The source archive contains `Sources/libunxip/libunxip.swift` as a symlink to `../../unxip.swift`; this is expected upstream layout.

## Test Strategy

- Upstream CI builds with `swift build --configuration release`.
- Upstream full runtime test downloads and decrypts a large Xcode `.xip` fixture, then extracts it. This is unsuitable for local preflight because it needs secrets and substantial disk/CPU time.
- `test_package` uses a lightweight CLI smoke test: `unxip --version` must equal `unxip 3.3`.

## Current Status

Conan recipe and `test_package` are prepared, but local `conan create` cannot complete until a Swift 6 toolchain is available on the OHOS worker.

Local `conan create archives\u\unxip\3.3 --user=ohpcd --channel=stable --build=missing`
was also attempted on this Windows host and stopped before dependency resolution
because `C:\Users\ylinz\.conan2\profiles\default` is not configured. No true-device
or shadow CI job was started.

True-device single-package CI was run after the device became available:

```sh
CI_PACKAGES="archives/u/unxip/3.3" zsh ci/conan/build_and_test.sh
```

Result:

- L0 passed. Dependency publication checks downloaded `libxml2/2.15.3`, `xz/5.6.2`, and `zlib-ng-compat/2.3.3` from `ohpcd`.
- L0k warned that this CLI package has no software-level `commands.json`; this was left unchanged to keep this round scoped to `archives/u/unxip/3.3`.
- `conan create` reached `build()` and failed with `Swift 6 toolchain not found on PATH`.
- L1 failed because `conan create` failed; L2/L4/L5 were skipped.
- Build summary: `Total: 1`, `Success: 0`, `Failed: 1`.
- Follow-up `command -v swift` and a limited `find "$HOME" /data/service/hnp -maxdepth 5 -type f -name swift` found no Swift executable on the device.

## Swift Toolchain Probe For Path B

Goal: collect evidence for a candidate Path B claim around Swift toolchain
availability/migration on OHOS, without mixing Swift toolchain adaptation into
the `unxip` recipe PR.

Official Swift 6.0.3 Ubuntu 22.04 aarch64 tarball was downloaded on the
HarmonyOS device:

- URL: `https://download.swift.org/swift-6.0.3-release/ubuntu2204-aarch64/swift-6.0.3-RELEASE/swift-6.0.3-RELEASE-ubuntu22.04-aarch64.tar.gz`
- Size: `736M`
- SHA256: `0ce755e7ed16fa07f6d1207a8135aff97e977653c1359011c60cb6d85a9cfa5b`
- Probe root: `/storage/Users/currentUser/swift-toolchain-probe`

Observed boundaries:

1. Tar extraction hit OHOS link-creation restrictions:
   `tar: can't link '.../usr/bin/swift' -> 'swift-driver': Permission denied`.
2. Directly running an extracted unsigned `swift-driver` returned
   `Permission denied`.
3. After signing `swift-driver` with `$HOME/usr/local/bin/binary-sign-tool`,
   execution changed to `No such file or directory`.
4. `$HOME/usr/local/bin/llvm-readobj` showed the binary requests
   `/lib/ld-linux-aarch64.so.1` and Linux/glibc libraries such as `libc.so.6`,
   `libm.so.6`, `libstdc++.so.6`, `libgcc_s.so.1`, `libncurses.so.6`,
   `libtinfo.so.6`, and `libsqlite3.so.0`.
5. The tested device does not provide `/lib/ld-linux-aarch64.so.1`.

Conclusion: official Swift Linux/aarch64 binaries are a valid upstream source,
but they are not directly usable as an OHOS native Swift 6 host toolchain. This
should be split into a dedicated Swift toolchain task/issue before retrying
`unxip`.

Follow-up source check: Swift's official Linux install page also publishes
`https://download.swift.org/swiftly/linux/swiftly-aarch64.tar.gz`. Local
`readelf` inspection of the extracted `swiftly` binary showed no `PT_INTERP`
and no dynamic section, so Swiftly is worth a later signed true-device probe.
It is only an installer/manager, though; the Swift compiler toolchains it
installs still need separate ELF loader/runtime verification.

Swiftly true-device probe was then run in
`/storage/Users/currentUser/swiftly-probe`. The unsigned `swiftly` binary hit
`Permission denied`; after signing and running it under the real executable name
`swiftly`, `--help` succeeded. `init --skip-install` failed on the stock binary
because the device has no system `ca-certificates` bundle and the system cert
directory is not writable by `currentUser`. Setting `SSL_CERT_FILE` to a user
CA bundle did not bypass Swiftly's hard-coded preflight check. A probe-only
binary patch redirected the hard-coded CA bundle path to
`/storage/Users/currentUser/a.pem`; after re-signing, `swiftly init --platform
ubuntu22.04 --skip-install --quiet-shell-followup --assume-yes` succeeded,
`swiftly --version` returned `1.1.3`, `swiftly list` succeeded, and
`swiftly list-available` listed Swift 6.0.3 among available releases. Full
`swiftly install 6.0.3` was not started because the device load was around 20
and SSH began closing connections before disk/GPG checks could complete.

Follow-up attempt: `swiftly install 6.0.3 --no-verify --assume-yes --use` was
started after SSH recovered, but stopped early with `The operation could not be
completed. The file doesn’t exist.` while reporting Swiftly was unlinked. A
subsequent verbose diagnostic command exceeded the local timeout and left one
`swiftly` process on the device. At 18:37, that `swiftly` process (PID 48646)
was terminated. No Swift toolchain was installed. An unrelated `conan` process
was left untouched.

Device load remained about 20, so the full Swift 6.0.3 install/probe was
deferred to the next low-load window.

2026-07-26 follow-up: no Swift/Conan/clang/make workload was visible, although
`uptime` still reported load around 20. `top` showed the CPUs mostly idle, so
the Swiftly probe resumed from `/storage/Users/currentUser/swiftly-probe`.
`swiftly list-available` continued to list Swift 6.0.3. Running:

```sh
swiftly install 6.0.3 --no-verify --assume-yes --use --verbose
```

downloaded the full `735.9 MiB` Swift 6.0.3 Ubuntu 22.04 aarch64 toolchain, but
installation failed during extraction:

```text
100%: Downloaded 735.9 MiB of 735.9 MiB
Error: ExtractError(message: Optional("Can't create '/storage/Users/currentUser/swiftly-probe/isolated-home/.local/share/swiftly/toolchains/6.0.3/usr/bin/aarch64-swift-linux-musl-clang++.cfg'"))
```

No installed Swift compiler was registered by `swiftly list`. This reinforces
that the next blocker is not only downloading Swift, but adapting/extracting the
Swift toolchain archive layout on the OHOS user filesystem before ELF runtime
verification can continue.

2026-07-26 04:00 heartbeat follow-up: no Apache/Arrow/Conan/clang/make/ninja or
Swiftly workload was visible. `uptime` still reported load around 20, but `top`
showed CPUs mostly idle. The existing verified tarball was reused:

```text
/storage/Users/currentUser/swift-toolchain-probe/swift-6.0.3-RELEASE-ubuntu22.04-aarch64.tar.gz
SHA256: 0ce755e7ed16fa07f6d1207a8135aff97e977653c1359011c60cb6d85a9cfa5b
```

The prior partial extraction already contained real target binaries such as
`swift-driver`, `swift-frontend`, `swift-package`, `clang-17`, and Swift runtime
libraries. A minimal link-flatten probe copied these link-style entries into
ordinary files under the extracted `usr/bin`:

```text
swift -> swift-driver
swiftc -> swift-driver
clang -> clang-17
aarch64-swift-linux-musl-clang++.cfg -> aarch64-swift-linux-musl-clang.cfg
```

`llvm-readobj` and `strings` confirmed that the resulting `swift` binary still
requests the Linux/glibc interpreter:

```text
PT_INTERP
/lib/ld-linux-aarch64.so.1
NEEDED: libc.so.6
NEEDED: libm.so.6
NEEDED: libstdc++.so.6
NEEDED: libgcc_s.so.1
NEEDED: libFoundation.so
RUNPATH: $ORIGIN/../lib/swift/linux
```

Unsigned `swift --version` returned `No such file or directory`. After signing
a `swift` copy with `$HOME/usr/local/bin/binary-sign-tool`, the signed copy
still returned `No such file or directory`. `swift-frontend` behaved the same.
The device still does not provide `/lib/ld-linux-aarch64.so.1`. This confirms
that link-flattening addresses archive layout only; it does not make the
official Ubuntu Swift 6.0.3 compiler executable on OHOS.

2026-07-26 glibc runtime bundle probe: Ubuntu 22.04 arm64 runtime packages were
resolved from `ports.ubuntu.com` and a minimal runtime bundle was built from:

- `libc6_2.35-0ubuntu3.13_arm64.deb`
- `libgcc-s1_12.3.0-1ubuntu1~22.04.3_arm64.deb`
- `libstdc++6_12.3.0-1ubuntu1~22.04.3_arm64.deb`
- `libncurses6_6.3-2ubuntu0.2_arm64.deb`
- `libtinfo6_6.3-2ubuntu0.2_arm64.deb`
- `libsqlite3-0_3.37.2-2ubuntu0.7_arm64.deb`
- `zlib1g_1.2.11.dfsg-2ubuntu9.2_arm64.deb`
- `libuuid1_2.37.2-4ubuntu3.5_arm64.deb`

Symlinks in the bundle were materialized as regular files before upload to avoid
OHOS link handling issues. The bundle contains `ld-linux-aarch64.so.1`,
`libc.so.6`, `libm.so.6`, `libstdc++.so.6`, `libgcc_s.so.1`,
`libncurses.so.6`, `libtinfo.so.6`, `libsqlite3.so.0`, `libz.so.1`, and
`libuuid.so.1`.

After signing `ld-linux-aarch64.so.1`, the loader itself can run and print
`--help`. This proves the loader binary can be executed when signed. However,
using that signed loader to run either original or signed Swift binaries fails:

```text
error while loading shared libraries: .../swift: failed to map segment from shared object
```

The same failure occurs with a minimal Ubuntu `coreutils` `true` binary:

```text
true_orig_exit=127
.../true.arm64: failed to map segment from shared object

true_signed_exit=127
.../true.signed: failed to map segment from shared object
```

Therefore the glibc runtime bundle route does not currently make Linux/glibc
executables usable on OHOS. The blocker is broader than Swift: signed glibc
loader execution works, but loader-mediated mapping of Linux ELF program
segments fails even for a small glibc executable.

Follow-up mount/execution check: `/storage/Users/currentUser` does not show an
explicit `noexec` mount flag, and signed Swiftly plus signed
`ld-linux-aarch64.so.1` both start from the probe paths. Direct execution of the
signed Ubuntu `true` binary still reports `No such file or directory` because
its PT_INTERP points to the Linux loader path; execution through the signed
loader reaches `failed to map segment from shared object`. A simple noexec
directory explanation is therefore unlikely.

2026-07-26 source follow-up: local archive/cmd-pkgs search did not find a
ready OHOS Swift host toolchain. The only Swift ecosystem recipe found locally
is `libdispatch/5.10.1`, which builds with Swift disabled and does not provide a
compiler. Official Swift install material still points to Linux/aarch64
toolchains, Swiftly, and Static Linux SDK workflows; those do not bypass the
current host-toolchain boundary because Static Linux SDK is driven by a working
host `swift`, and Swift source builds also require a prebuilt Swift toolchain to
bootstrap Swift components. A lightweight string scan of the extracted official
Swift 6.0.3 package found no `ohos`, `OpenHarmony`, or
`aarch64.*linux.*ohos` target markers in common text/config files or in
`swift-driver`, `swift-frontend`, and `clang-17`.

2026-07-26 mainline direction follow-up: the detailed note is
`reports/swift-mainline-ohos.md`. The OHOS-native C/C++ substrate is usable on
the device when invoked correctly: `$HOME/usr/local/bin/clang-15` reports target
`aarch64-unknown-linux-ohos`; the `clang`/`clang++` wrappers must be invoked via
`sh ./clang` and `sh ./clang++`; `TMPDIR` must be set to a writable user
directory. With those constraints, a C smoke binary built and ran with exit 0,
and a C++ smoke binary built and printed `42`. This confirms the local
AArch64/OHOS LLVM substrate, but the missing work remains Swift-specific:
OHOS triple/platform support in Swift/SwiftPM, OHOS Swift runtime/stdlib, a
Linux-bootstrap cross-build of OHOS-host Swift tools, signing, and finally
`swift --version` on the device.

Path B application issue: `#1438`
(`https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1438`).

Path B candidate evidence is summarized in `path-b-evidence.md`. The reusable
knowledge draft is `knowledge/graph/draft/E232-draft-unxip-swift-toolchain-ohos.*`.

2026-07-28 Swift source-build follow-up: the mainline OHOS-native Swift host
toolchain path is now being tested directly on the true device under
`/storage/Users/currentUser/swift-mainline-ohos-src`. The build uses the OHOS
LLVM fork/toolchain (`clang-15`, target `aarch64-unknown-linux-ohos`) and a
writable `TMPDIR` at
`/storage/Users/currentUser/swift-mainline-ohos-src/tmp`.

The incremental `ninja -j4 swift-frontend` build has moved beyond the earlier
IRGen and TextAPI blockers. Verified progress includes successful compilation
or linking of major frontend prerequisites after local compatibility patches:
`MetadataRequest.cpp`, `TBDGen.cpp`, `swiftClangImporter` prerequisites,
`libswiftLLVMPasses.a`, and rebuilt `swiftBasic`/`swiftAST` portions after CAS
shim updates.

The 2026-07-28 22:43 CST rebuild validated the next CAS shim layer. Additional
LLVM15 compatibility shims were added and synced to the device:

- `ObjectStore::createUnknownObjectError(const CASID &)`;
- `ObjectProxy::getData()` returning `StringRef` for cached diagnostics and
  VFS output replay, with `getDataArray()` retained for array-style callers;
- `AsyncProxyValue` wrapper with `.take()` so Swift's newer CAS future API can
  compile against LLVM15;
- `operator<<(raw_ostream &, const CASID &)` for cache result printing.

After those changes, the build passed the previous `CachingUtils.cpp` and
`CompileJobCacheResult.cpp` failures, rebuilt through `libswiftAST.a`,
`libswiftSIL.a`, and reached `[270/807]` in `lib/Sema`. It was then stopped
deliberately with `BUILD_EXIT=2` because another true-device `vapoursynth`
Conan heavy task had started. No new Swift source or linker failure was
observed before the manual pause.

After the issue update, the device became idle again and the same build was
resumed at 23:00 CST. The incremental graph started at `[1/537]`, confirming
the earlier objects were retained, linked `libswiftSema.a`, entered
`lib/SILGen` and then `lib/SILOptimizer`, and reached `[139/537]`
(approximately `[409/807]` in the original graph) at
`lib/SILOptimizer/Differentiation/Common.cpp.o`. A second `vapoursynth` Conan
heavy task then started at 23:06 CST, so the Swift build was again stopped
deliberately with `BUILD_EXIT=2`. No new Swift compile or link failure was
observed before this pause.

The build was resumed again at 23:55 CST from the same directory. The
incremental graph started at `[1/398]`, advanced through more of
`lib/SILOptimizer`, entered `lib/IRGen`, and reached `[218/398]` at
`lib/IRGen/GenClangType.cpp.o`. At 00:03 CST a separate `xapian-core` Conan
heavy task started on the true device, so the Swift build was paused again at
00:05 CST with `BUILD_EXIT=2`. No new Swift compile or link failure was
observed before this pause.

At 00:08 CST the build resumed from the IRGen/Frontend tail. The
`CompilerInvocation.cpp` fixes were validated, `SerializedDiagnosticConsumer`
then exposed an older Clang serialized diagnostics enum missing
`RECORD_SOURCE_FILE_CONTENTS`, and the Clang compatibility header was extended
accordingly. The next run compiled `SerializedDiagnosticConsumer.cpp` and
linked `libswiftIRGen.a`, proving both fixes. The following boundary is an
OHOS filesystem behavior: the build directory was configured with
`SWIFT_USE_SYMLINKS=ON`, and CMake failed to create migrator JSON symlinks with
`Permission denied`. The next build-system step is to reconfigure the same
build directory with `SWIFT_USE_SYMLINKS=OFF` so Swift uses
`copy_if_different`/`copy_directory` instead of `create_symlink`.

2026-07-29 afternoon follow-up: after reconfiguring away from the symlink
boundary and continuing the source build, the OHOS-native Swift host binaries
were produced under
`/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/bin`.
The resulting `swift`, `swiftc`, and `swift-frontend` binaries are signed
OHOS-runnable ELF files and `swift --version` reports:

```text
Swift version 6.0.3 (swift-6.0.3-RELEASE)
Target: aarch64-unknown-linux-ohos
```

The current technical boundary is now narrower than host executable startup:
clean-cache `import SwiftShims` crashes while Clang builds the SwiftShims PCM.
If a crashing run leaves `SwiftShims.pcm` in the module cache, a cache-reuse
probe can pass, so the failure is tied to first-time Clang module/PCM creation
or finalization rather than Swift frontend process launch.

Additional LLVM15 compatibility work was validated on 2026-07-29:

- rebuilt `libclangFrontend.a` after temporary `[ohos-probe-fa]` diagnostics in
  `clang/lib/Frontend/FrontendAction.cpp`;
- added zlib/zstd `decompress(...)` compatibility aliases in
  `llvm/include/llvm/Support/Compression.h`;
- removed a stale 3-parameter `SetVector` forward declaration in
  `llvm/utils/TableGen/CodeGenRegisters.h`;
- rebuilt stale `libLLVMipo.a` and `libLLVMLTO.a` after the SetVector ABI
  change;
- rebuilt `swift-frontend` successfully after those LLVM static archives were
  made consistent.

Latest validated logs:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/rebuild-llvm-host-clangFrontend-cxx17-native-20260729-140038.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/rebuild-swift-frontend-after-ipo-lto-20260729-143536.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftshims-after-fa-no-modulemap-20260729-144131.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftshims-after-fa-explicit-modulemap-20260729-144135.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/rebuild-swift-frontend-fa2-20260729-145039.log
```

The latest probe showed the crash occurs after
`CreateWrappedASTConsumer(CI, PresumedInputFile)` returns a non-null consumer
and before the previously placed marker for `setASTMutationListener`. A finer
diagnostic marker patch has been synced to the true-device LLVM source at
`/storage/Users/currentUser/swift-mainline-ohos-src/repos/llvm-project/clang/lib/Frontend/FrontendAction.cpp`,
but it has not been rebuilt yet because `apache-arrow-glib` true-device Conan
tasks were active again at 2026-07-29 15:23 CST.

2026-07-29 16:00 CST follow-up: the clean-cache `SwiftShims` probe was narrowed
past `PCHGenerator::Writer.WriteAST` and into the object PCH container backend.
The latest diagnostic log is:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftshims-objpch-no-modulemap-20260729-160307.log
```

The last emitted marker before the trap was
`[ohos-probe-objpch] before EmitBackendOutput EmitObj`, with no marker after
`clang::EmitBackendOutput(... Backend_EmitObj ...)`. A minimal Swift-side
experiment was prepared in
`/storage/Users/currentUser/swift-mainline-ohos-src/repos/swift/lib/ClangImporter/ClangImporter.cpp`
to use raw Clang module containers for OHOS targets: OHOS now requests
`-fmodule-format=raw`, skips `ObjectFilePCHContainerWriter/Reader`, and disables
`DebugTypeExtRefs` for that raw-container path. The synced file hash is:

```text
d67b2fc73ab4ff7807b4971b4a833e05135ace63afe8adf3aa111e19e402f0c6
```

This patch has not yet been rebuilt or probed. At 2026-07-29 16:13 CST the true
device was running an `apache-arrow-glib` Conan/CMake build with `make -j20` and
many active `clang-15` processes, so no Swift rebuild was started in this
resource window.

After the device cleared, the raw-container experiment was rebuilt and
validated:

- `ninja -v -j2 swift-frontend` completed with `RC=0` and rebuilt
  `libswiftClangImporter.a` plus `bin/swift-frontend`. Log:
  `/storage/Users/currentUser/swift-mainline-ohos-src/logs/rebuild-swift-frontend-rawpcm-20260729-163158.log`.
- A corrected clean-cache `import SwiftShims` probe completed with `RC=0`.
  The log shows `PCHGenerator::Writer.WriteAST` completing, then
  `RawPCHContainerWriter` writing and flushing `SwiftShims.pcm` without
  entering the previous object-container `EmitObj` crash path. Log:
  `/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftshims-rawpcm-clean2-20260729-163400.log`.
- `ninja -v -j2 swiftCore-swiftmodule-ohos-aarch64` completed with `RC=0` and
  produced the OHOS/aarch64 Swift standard-library module files:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos/Swift.swiftmodule/aarch64-unknown-linux-ohos.swiftmodule
sha256 e33a13e2d3537a65f4318e0e1dff4dc2cf70eba646fb4080c05966c4f83f69c3

/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos/Swift.swiftmodule/aarch64-unknown-linux-ohos.swiftdoc
sha256 c74ec2548acd38937e8b4517c2928a5bdfb815d59b79eb0e072ddcca58d30a08
```

The Swift driver still starts and reports Swift 6.0.3 for
`aarch64-unknown-linux-ohos` after these rebuilds.

### 2026-07-30 SwiftCore Runtime Progress

The next heavy Swift target, `swiftCore-ohos-aarch64`, has now passed on the
true device after two additional OHOS-specific toolchain experiments:

- The first direct `swiftCore-ohos-aarch64` object build reached the Swift
  embedded AArch64 backend and crashed in `AArch64 Assembly Printer` while
  emitting `stdlib/public/core/OHOS/aarch64/Swift.o`. Replacing `-g` with
  `-gnone` did not change the failure, so it was not just debug info emission.
- Re-running the same frontend command as `-emit-ir` produced a 94 MiB
  `Swift.ll` despite returning signal 5. Compiling that IR through the OHOS
  LLVM fork succeeded:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/compile-Swift-ll-ohos-clang-20260730-111748.log
RC=0
Swift.from-ll.o: 20 MiB aarch64 ELF relocatable
```

- A temporary `swiftc` wrapper in the remote build directory now intercepts
  only the OHOS stdlib `Swift.o` command, emits IR, tolerates the post-IR
  frontend trap when the `.ll` is non-empty, and compiles `Swift.ll` with the
  OHOS `clang-15` wrapper. Ordinary `swiftc` invocations still pass through to
  the original binary.
- With `Swift.o` bypassed, the build reached the `libswiftCore.so` link and
  exposed a second boundary: several runtime/support object targets were built
  without `-fPIC`. A generated `build.ninja` experiment added `-fPIC` to 95
  OHOS/aarch64 runtime/support compile edges that feed `libswiftCore.so`.

The final rerun completed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swiftCore-ohos-aarch64-pic-runtime-20260730-115544.log
RC=0

/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos/aarch64/libswiftCore.so
34 MiB, ELF shared object, 64-bit LSB arm64, BuildID=d7e061516e32de23c986b7dd3d5735482631b558
```

Current boundary has therefore moved from `SwiftShims` and `Swift.o` generation
to the broader stdlib target `stdlib/swift-stdlib-ohos-aarch64`. The two latest
workarounds are still experimental build-tree changes, not a polished upstream
patch: the source-level follow-up should replace the `swiftc` wrapper with a
proper OHOS IR/object emission strategy or backend fix, and replace the
generated `build.ninja` patch with a CMake-side PIC fix for OHOS runtime/support
targets.

### 2026-07-30 SwiftGlibc Overlay / Sysroot Probe

The next stdlib boundary was the missing
`stdlib/private/RuntimeUnittest/swiftGlibc-swiftmodule-ohos-aarch64` dependency.
Inspection showed `stdlib/public/Platform/CMakeLists.txt` did not include OHOS
in `swiftGlibc_target_sdks`, and its `glibc_modulemap` generation loop also
filtered OHOS out. A remote source experiment added OHOS to the Glibc overlay
target set and excluded OHOS from the `glibc.modulemap.gyb` `link "dl"` rule,
because OHOS resolves `dl` through libc rather than a separate `libdl`.

That regenerated the expected Ninja targets, including
`swiftGlibc-swiftmodule-ohos-aarch64`, and generated:

```text
lib/swift/ohos/aarch64/glibc.modulemap
lib/swift/ohos/aarch64/SwiftGlibc.h
```

Two environment/header boundaries were then exposed:

- without `TMPDIR=/storage/Users/currentUser/swift-mainline-ohos-src/tmp`,
  Swift driver module emission failed with
  `Read-only file system - unable to create temporary file for supplementaryOutputs`;
- with `TMPDIR` fixed, `SwiftOverlayShims` first failed on missing
  `<semaphore.h>`, so `LibcOverlayShims.h` was patched to guard semaphore shims
  with `__has_include(<semaphore.h>)`.

The following failure showed that the Swift stdlib OHOS SDK path was still `/`,
so ClangImporter could not see the staged OHOS sysroot headers and failed on
`<sys/ioctl.h>`. Reconfiguring with
`-DSWIFT_SDK_OHOS_ARCH_aarch64_PATH=/storage/Users/currentUser/usr/local/sysroot`
changed the generated Swift commands from `-sdk /` to the real sysroot path.

The sysroot rerun used:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swiftGlibc-ohos-aarch64-sysroot-20260730-122806.log
```

It progressed through a wide CMake-regenerated dependency rebuild from the
Glibc overlay target to at least `[471/916]` with no recorded compile error.
After that point the device entered sustained memory pressure: SSH commands
reported `Out of memory` or `can't fork`, and the run was treated as a resource
boundary rather than a confirmed Swift source failure. A terminate signal was
sent to the last observed build parent PID `45978`; final remote state still
needs confirmation once SSH sessions are stable again.

2026-07-30 14:56 CST reconnection check: the original Swift build device
`10.62.230.12` still answered ping, but both direct SSH `10.62.230.12:2222`
and its old-O SakuraFrp tunnel `frp-tip.com:56267` refused TCP connections
through six short retries. The second O machine at `frp-tip.com:33332` was
reachable and idle enough for checks, but it did not contain
`/storage/Users/currentUser/swift-mainline-ohos-src`, so it cannot resume the
existing Swift incremental build without a fresh source/build-tree transfer.
No new Swift build was started during this disconnected window.

Next steps for this lane:

- confirm whether the sysroot `swiftGlibc` run exited, was killed, or left a
  partial Ninja state;
- resume with a narrower target if possible, or avoid a full host-tool rebuild
  by restoring the already-built host artifacts before retrying the overlay;
- keep `TMPDIR` and the real OHOS sysroot path as required build environment;
- move the OHOS Glibc overlay target, modulemap conditions, semaphore guard,
  and sysroot path handling into source-level CMake/shim patches instead of
  generated build-tree edits.

Important latest build log:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swift-build-frontend-20260728-235546.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swift-build-frontend-20260729-000815.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swift-build-frontend-20260729-001351.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swift-build-frontend-20260729-001634.log
```

Current build boundary is still the Swift host toolchain itself, not `unxip`.
Do not run `unxip` single-package CI until an OHOS-runnable `swift` or
`swift-frontend` binary exists and passes ELF/signing/runtime checks.

### 2026-07-30 Evening SwiftGlibc Modulemap Resume

The SwiftGlibc blocker was narrowed from a missing Ninja target to ClangImporter
modulemap visibility and OHOS libc header differences.

Observed failure:

```text
error: no such module 'SwiftGlibc'
@_exported import SwiftGlibc
```

A manual probe proved that explicitly passing the generated OHOS modulemap with
`-Xcc -fmodule-map-file=.../lib/swift/ohos/aarch64/glibc.modulemap` changes the
failure from a module lookup miss to concrete modulemap/header diagnostics. The
generated `glibc.modulemap` and
`sysroot-relative-modulemaps/glibc.modulemap` were then patched in the remote
build tree to resolve `assert.h` through the staged OHOS sysroot and to remove
the unavailable `CUUID` block that references `uuid/uuid.h`.

The OHOS sysroot also does not expose glibc private `__sighandler_t`, so the
remote `Platform.swift` experiment now maps OHOS `sighandler_t` to the public C
function pointer shape:

```swift
#if SWIFT_STDLIB_OS_OHOS
public typealias sighandler_t = @convention(c) (Int32) -> Void
#else
public typealias sighandler_t = __sighandler_t
#endif
```

With those build-tree/source experiments and the SwiftGlibc Ninja command
patched to include the explicit modulemap and `-D SWIFT_STDLIB_OS_OHOS`, the
target completed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swiftGlibc-swiftmodule-ohos-aarch64-flags-20260730-184945.log
RC=0
```

The broader stdlib/runtime chain was then resumed with:

```sh
TMPDIR=/storage/Users/currentUser/swift-mainline-ohos-src/tmp \
SWIFT_SDK_OHOS_ARCH_aarch64_PATH=/storage/Users/currentUser/usr/local/sysroot \
nice -n 10 ninja -v -j1 stdlib/swift-stdlib-ohos-aarch64
```

Two previously known Swift backend object-emission crashes were handled with
remote build-tree IR handoff experiments:

- `Swift.o` now reuses the already validated `Swift.from-ll.o`.
- `SwiftOnoneSupport.o` was produced by compiling `SwiftOnoneSupport.ll` through
  the OHOS clang wrapper, then the Ninja edge was patched to copy the resulting
  `SwiftOnoneSupport.from-ll.o`.

The next link attempt reached `libswiftCore.so` and exposed non-PIC runtime
objects. A generated `build.ninja` experiment added `-fPIC` to OHOS/aarch64
C/C++ compile flags. The follow-up full-chain run is intentionally constrained
to `ninja -j1` and `nice -n 10` to avoid repeating the previous device pressure
event. As of 2026-07-30 19:25 CST it was still running, had reached
`[132/1086]`, showed about 14 GiB available memory, and had no new
`FAILED`, `error:`, or `Segmentation fault` marker in:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-stdlib-ohos-aarch64-full-j1-20260730-191240.log
```

This keeps `unxip` itself blocked on Swift stdlib/runtime completion; do not
start `unxip` CI until this Swift host/runtime lane produces a runnable,
signed, OHOS-target-capable Swift toolchain and the stdlib artifacts required by
SwiftPM.

### 2026-07-30 Late Evening Stdlib Runtime Resume

The broad stdlib graph advanced past the SwiftGlibc search-path boundary and
several private stdlib object targets. Device monitoring stayed conservative:
all resumed full-graph runs used `nice -n 10 ninja -j1`, and watchdog samples
showed roughly 14 GiB `MemAvailable` during the short runners.

Confirmed progress:

- `SwiftGlibc` modulemap lookup is no longer the active failure. The generated
  OHOS `glibc.modulemap` is passed explicitly with
  `-Xcc -fmodule-map-file=.../lib/swift/ohos/aarch64/glibc.modulemap`.
- `SwiftPrivate.o` failed in object emission, but the corrected `-emit-ir`
  probe produced `SwiftPrivate.correct.ll` (about 700 KiB). `opt -verify`,
  `opt -S -strip-debug`, and the OHOS clang wrapper produced
  `SwiftPrivate.strip-clang.o` (about 123 KiB), and the single Ninja edge was
  patched to copy it. Verification log:
  `/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-SwiftPrivate-ll-opt-clang-20260730-221949.log`.
- `SwiftPrivateLibcExtras.o` hit the same IRGen/backend class. The corrected
  `-emit-ir` probe produced `SwiftPrivateLibcExtras.correct.ll` (about
  530 KiB), and the stripped IR compiled through OHOS clang into
  `SwiftPrivateLibcExtras.strip-clang.o` (about 92 KiB). Verification log:
  `/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-SwiftPrivateLibcExtras-ll-opt-clang-20260730-222354.log`.
- `SwiftPrivateThreadExtras.swift` exposed an OHOS pthread import difference:
  OHOS imports `pthread_t` as an opaque pointer shape, while upstream's Linux
  branch expects `pthread_t()` to be default-constructible. The remote source
  experiment changes the Linux/Android `_make_pthread_t()` branch to exclude
  `SWIFT_STDLIB_OS_OHOS`, so OHOS uses the optional `nil` initializer path.
- The generated OHOS Swift compile commands were also patched to pass
  `-D SWIFT_STDLIB_OS_OHOS` globally for target Swift commands; 46 commands
  were updated in `build.ninja`.
- After the pthread fix, `SwiftPrivateThreadExtras.o` moved from type errors to
  the same object-emission crash class. A watchdog-wrapped probe produced
  `SwiftPrivateThreadExtras.correct.ll` (about 359 KiB) and an object-ready
  `SwiftPrivateThreadExtras.strip-clang.o`. Probe status:
  `/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-SwiftPrivateThreadExtras-20260730-223719.status`.
- After SSH recovered, the `SwiftPrivateThreadExtras.o` single-edge copy rule
  was confirmed and executed. The target object is now a 64 KiB arm64 ELF
  relocatable copied from `SwiftPrivateThreadExtras.strip-clang.o`; backup:
  `/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/build.ninja.pre-ohos-SwiftPrivateThreadExtras-copy-20260730-224259.bak`.

Boundary before the final resume:

- SSH to `10.62.230.12:2222` reset during key exchange twice during this
  window, then recovered. No broad package CI was started during the reset.
  The next action was to resume `stdlib/swift-stdlib-ohos-aarch64` with the same
  watchdog runner and capture the next source/backend boundary.

### 2026-07-30 Final Stdlib Runtime Pass

The next constrained resume completed the full OHOS stdlib/runtime target:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-stdlib-ohos-aarch64-full-j1-20260730-230325.log
END=2026-07-30 23:04:01 CST rc=0
```

This confirms the two requested frontiers for this round:

- `SwiftGlibc` modulemap lookup is fixed in the generated build command. A
  direct grep of `build.ninja` now finds:
  `-fmodule-map-file=/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos/aarch64/glibc.modulemap`.
- A lightweight true-device typecheck of `import Glibc` using that modulemap and
  the staged OHOS sysroot returned `typecheck_rc=0`.
- `swift --version` and `swiftc --version` both return Swift 6.0.3 with target
  `aarch64-unknown-linux-ohos`.
- `nice -n 10 ninja -n stdlib/swift-stdlib-ohos-aarch64` returned
  `ninja_dry_rc=0`; the dry run listed only five host helper/share regeneration
  actions and no new OHOS stdlib/runtime library edge.

Produced/copied OHOS stdlib/runtime artifacts under
`$B/lib/swift/ohos/aarch64` include:

```text
34M  libswiftCore.so
119K libswiftGlibc.so
22M  libswiftRemoteMirror.so
79K  libswiftRuntimeUnittest.so
3.8M libswiftStdlibCollectionUnittest.so
199K libswiftStdlibUnicodeUnittest.so
987K libswiftStdlibUnittest.so
96K  libswiftSwiftOnoneSupport.so
139K libswiftSwiftPrivate.so
111K libswiftSwiftPrivateLibcExtras.so
91K  libswiftSwiftPrivateThreadExtras.so
55K  libswift_Builtin_float.so
```

Installed OHOS Swift modules include `Swift`, `Glibc`,
`SwiftOnoneSupport`, `SwiftPrivate`, `SwiftPrivateLibcExtras`,
`SwiftPrivateThreadExtras`, `_Builtin_float`, `RuntimeUnittest`,
`StdlibUnittest`, `StdlibUnicodeUnittest`, and `StdlibCollectionUnittest`, each
as `aarch64-unknown-linux-ohos.swiftmodule`.

Dynamic dependency spot checks:

```text
libswiftCore.so:  NEEDED libc++_shared.so, libc.so
libswiftGlibc.so: NEEDED libswiftSwiftOnoneSupport.so, libswiftCore.so,
                  libc++_shared.so, libc.so
```

Device health after the pass was stable: `MemAvailable` stayed around
14 GiB, and the heavy-process scan showed no active
Apache/Arrow/Conan/clang/ninja/make/Swiftly workload apart from the SSH
listener. Load average remained around 20, which is acceptable per the current
resource rule from the user.

Remaining boundary: this is still a remote experimental Swift build tree, not a
clean source-level Swift toolchain patch series or packaged Conan toolchain.
The temporary IR-to-OHOS-clang handoff, generated `-fPIC` propagation, OHOS
Glibc overlay/modulemap edits, raw PCM ClangImporter route, pthread model fix,
and signing/runtime assumptions need to be converted into reproducible patches
before retrying `unxip` SwiftPM CI.

### 2026-07-30 User Program Smoke Boundary

After the stdlib/runtime pass, direct user-level `swiftc` compilation still
exits through signal 5, but the frontend leaves complete LLVM IR for simple
programs. A constrained IR handoff can verify, strip, compile, link, sign, and
run those programs through the OHOS LLVM/clang path.

Minimal `print` smoke:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-hello-ir-continue-20260730-233205.log
verify_rc=0
strip_rc=0
object_rc=0
link_rc=0
sign_rc=0
hello-ohos-swift
run_rc=0
```

Minimal `import Glibc` smoke:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-hello-glibc-ir-run-20260730-234506.log
emit_ir_rc=133
script_emit_phase_rc=0
verify_rc=0
strip_rc=0
object_rc=0
autolink_rc=0
autolink_content:
-lswiftSwiftOnoneSupport
-lswiftCore
-lswiftGlibc
link_rc=0
sign_rc=0
hello-ohos-glibc
run_rc=0
```

The `emit_ir_rc=133` value confirms the active remaining toolchain defect:
`swiftc -frontend -emit-ir` still traps after producing usable IR. This makes
the IR handoff a proof of runtime viability, not yet a clean compiler fix.

SwiftPM is still not available from this build tree:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swift-package-version.log
error: unable to invoke subcommand: swift-package (No such file or directory)

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swift-build-help.log
error: unable to invoke subcommand: swift-build (No such file or directory)
```

An LLDB backtrace route was attempted but is not currently useful because the
available `liblldb.so` fails relocation on missing Python 3.11 symbols such as
`_Py_IsFinalizing` and `PyLong_AsUnsignedLongLongMask`.

### 2026-07-31 Swift Frontend Signal 5 Root Cause

The next true-device probe narrowed the user compile `signal 5` boundary from
"IRGen/backend" to a specific LLVM object lifetime issue on OHOS:

- `typecheck`, `emit-silgen`, and `emit-sil` for a minimal Swift file returned
  rc 0.
- `emit-irgen` and `emit-ir` originally wrote complete IR, then trapped with
  signal 5.
- Narrow markers showed `IRGenRequest::evaluate`, `IRGenModule::finalize`,
  `embedBitcode`, `IRGenModule::intoGeneratedModule`, `IRGenModule` destructor,
  `performLLVM`, and `generateCode` all completed.
- The crash occurred in `GeneratedModule` destruction, specifically at
  `TargetMachine.reset()`.

Diagnostic build/log:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swift-frontend-gm-reset-marker-20260731-003703.log
END=2026-07-31 00:39:26 CST rc=0

/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-gm-reset-marker-20260731-003944.log
[ohos-probe-gm] dtor begin context=... module=... target=...
[ohos-probe-gm] before reset TargetMachine
Signal 5 (core dumped)
```

A temporary OHOS-host workaround that releases, rather than destroys, the
`GeneratedModule` `TargetMachine` allowed the same minimal frontend path to
return successfully:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swift-frontend-gm-target-release-20260731-004023.log
END=2026-07-31 00:42:46 CST rc=0

/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-gm-target-release-20260731-004308.log
[ohos-probe-gm] after release TargetMachine ptr=...
[ohos-probe-gm] after reset Module
[ohos-probe-gm] after reset Context
[ohos-probe-ft] after performAction hadError=0 returnValue=0
rc=0
```

Follow-up checks after that workaround:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-after-target-release-20260731-004347-emit-ir.log
emit_ir_rc=0

/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-after-target-release-20260731-004347-c.log
frontend_c_rc=0
produced arm64 ELF relocatable object

/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-driver-after-target-release-20260731-004430-glibc-emit-ir.log
glibc_emit_ir_rc=0
```

The next boundary is no longer the Swift frontend IR/object action itself.
`swiftc` legacy driver proceeds past frontend compilation, but the complete
driver link still fails in the follow-up command chain. With `TMPDIR` set to
the writable Swift probe directory, the driver dry run shows it still chooses:

```text
/storage/Users/currentUser/usr/local/bin/clang -fuse-ld=gold ... --target=aarch64-unknown-linux-ohos
```

That differs from the manually successful OHOS link route, which used the
project's `toolchain/ohos-clang` wrapper and lld-shaped signing/link flags.
This means the next clean adaptation step is to remove noisy probe logging,
formalize the OHOS `TargetMachine` lifetime workaround, then fix the legacy
driver's OHOS linker selection or wrapper path. SwiftPM remains absent.

## 2026-07-31 Swift Driver Link Breakthrough

The remote Swift source tree was cleaned of the `FrontendTool.cpp`
`ohos-probe-ft` marker prints and rebuilt with the OHOS `TargetMachine`
lifetime workaround in place:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swift-frontend-clean-targetmachine-release-20260731-005549.log
[17/17] Linking CXX executable bin/swift-frontend
rc=0
```

Clean frontend checks then returned successfully without the previous signal 5
trap:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-clean-frontend-20260731-010143-emit-ir.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-clean-frontend-20260731-010143-c.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-clean-frontend-20260731-010143-glibc-emit-ir.log
RC emit_ir=0 frontend_c=0 glibc_emit_ir=0
```

The next blocker was isolated to the legacy driver link job. The driver-generated
frontend command and `swift-autolink-extract` both returned rc 0, while direct
execution of the shell clang wrapper failed with rc 126:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-driver-segments-20260731-010632.frontend.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-driver-segments-20260731-010632.autolink.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-driver-segments-20260731-010632.link.log
RC frontend=0 autolink=0 link=126
sh: .../usr/local/bin/clang: Permission denied
```

This proved that OHOS/HMDFS can execute the real `clang-15` ELF but cannot let
Swift's process launcher directly exec the shell wrapper. A source-level
experimental driver patch now does three OHOS-specific things:

- defaults the GenericUnix linker to `lld` for `isOHOSFamily()`;
- adds `-Wl,--code-sign` to OHOS dynamic link jobs;
- uses `clang-15` as the OHOS linker driver instead of the shell `clang`
  wrapper.

Rebuild and verification:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swift-frontend-ohos-driver-link-20260731-011056.log
[9/9] Linking CXX executable bin/swift-frontend
RC=0

/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-driver-after-ohos-link-20260731-011242.dry.log
.../usr/local/bin/clang-15 -fuse-ld=lld -pie -Wl,--code-sign ...

/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-driver-after-ohos-link-20260731-011242.log
DRY_RC=0 RUN_RC=0
hello after driver patch
EXE_RC=0
```

This is the first evidence in this thread that the OHOS-hosted Swift 6.0.3
`swiftc` legacy driver can compile, autolink, link/sign, and run a Swift user
program directly. It remains experimental because other historical probe prints
are still present in `ASTContext`, `SearchPathOptions`, `ClangImporter`,
`Frontend`, `ModuleInterfaceLoader`, and `SerializedModuleLoader`, and because
`swift-driver-new`, `swift-package`, and `swift-build` are still absent.

## 2026-07-31 Swift Driver Dependency Chain Probe

The next probe moved from the compiler binary to the missing `swift-driver-new`
layer. `repos/swift-driver` and `repos/swiftpm` exist on the true device, but
the main Swift compiler build graph does not include `swift-driver`,
`swift-package`, or `swift-build` targets.

`swift-driver` CMake can configure with the experimental OHOS `swiftc`, but its
dependency chain is not staged on the device. The first direct build failed on
missing `TSCBasic`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swift-driver-ohos-probe2-20260731-012633.log
error: no such module 'TSCBasic'
RC=1
```

The pinned dependency revisions from `repos/swift-driver/Package.resolved` were
fetched on the Windows host and transferred to the true device because the
device lacks `git`/`curl`:

```text
swift-argument-parser 8f4d2753f0e4778c76d5f05ad16c74f707390531
swift-llbuild        a3b8d34be319f1b3ba8de53c434386419dec1f4f
swift-tools-support-core 3b13e439a341bbbfe0f710c7d1be37221745ef1a
Yams                 0d9ee7ea8c4ebd4a489ad7a73d5c6cad55d6fed3
swift-system         025bcb1165deab2e20d4eaba79967ce73013f496
```

After pre-populating CMake `_deps`, configuration advanced through these
additional platform boundaries:

- CMake tried to use `/storage/Users/currentUser/usr/local/bin/clang++`, a shell
  wrapper that OHOS/HMDFS rejects when directly execed. Reconfiguring CXX to
  real `clang-15` with `CMAKE_CXX_COMPILER_ARG1=--driver-mode=g++` fixed that
  layer.
- `llbuild` required SQLite3 headers/library. A temporary staging SQLite
  3.49.1 was built from the existing repository recipe source:
  `/storage/Users/currentUser/swift-mainline-ohos-src/stage/sqlite3-3.49.1-ohos`.
- `TSC` required `SwiftSystemConfig.cmake`, so `swift-system` was configured as
  a separate package.
- SwiftSystem exposed an OHOS header-import issue: `O_ACCMODE` in OHOS
  `fcntl.h` expands through `O_SEARCH`, which ClangImporter marks unavailable.
  A minimal OHOS source experiment changes SwiftSystem's `_O_ACCMODE` to
  `03 | O_PATH`; `O_PATH` imports cleanly.

SwiftSystem then reached a familiar compiler backend boundary. Direct object
emission for `SystemPackage` crashes with signal 11 even with
`CMAKE_Swift_COMPILATION_MODE=wholemodule` and `CMAKE_Swift_NUM_THREADS=1`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-install-swift-system-ohos-wmo-20260731-015452.log
Program arguments: ... swiftc -frontend -c -primary-file .../Sources/System/Errno.swift ...
Signal 11
```

Changing the same frontend command from `-c` to `-emit-ir`, while keeping the
CMake side outputs, succeeds:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-swiftsystem-errno-emit-ir-20260731-015452.log
RC=0
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-swiftsystem-errno-emit-ir-20260731-015452.ll
OUT_SIZE=292096
```

So the current `swift-driver-new` path is not blocked at dependency resolution
anymore; it is blocked at the next SwiftSystem object-emission crash. The
probable continuation is an IR-to-OHOS-clang object handoff or a source-level
fix for this frontend/backend crash, followed by rebuilding SwiftSystem, TSC,
LLBuild, and finally `swift-driver`.

## Next Verification Commands

After Swift is available:

```sh
CI_PACKAGES="archives/u/unxip/3.3" zsh ci/conan/build_and_test.sh
```

Shadow CI single-package form:

```sh
/path/to/run-ohos-shadow-ci.sh archives/u/unxip/3.3
```

## 2026-07-31 FoundationCollections IR Handoff Probe

After SwiftSystem and libdispatch were staged through the same IR-to-OHOS-clang
handoff pattern, the Foundation probe was configured with XML and Networking
disabled for the first core-module pass. Configuration succeeded:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/configure-foundation-ohos-probe1-20260731-033718.log
CONFIG_RC=0
```

The first direct build target still fails at `_FoundationCollections` direct
object emission:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-foundation-ohos-probe1-j1-20260731-033842.log
_FoundationCollections
signal 11
```

A driver-level `swiftc -emit-ir -wmo` probe returned rc 254/signal 5, but left
a non-empty `_FoundationCollections.ll`. Because the generated output-filelist
mapped many inputs to one IR path, that artifact is evidence that IR emission
can progress, but it is not a safe complete target artifact:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationcollections-driver-emit-ir-20260731-035151.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/foundationcollections-driver-emit-ir-20260731-035151
```

The current mainline experiment therefore switched to primary-file IR handoff:
emit the `_FoundationCollections` module once, then for a bounded set of
primary sources run `swiftc -frontend -emit-ir`, `opt -verify`, `opt -S
-strip-debug`, and the OHOS clang wrapper to produce the corresponding CMake
object path. Two bounded probes passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationcollections-primary-handoff-20260731-040138.log
limit=5
END=2026-07-31 04:05:12 CST rc=0

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationcollections-primary-handoff-20260731-040621.log
limit=20
END=2026-07-31 04:13:24 CST rc=0

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationcollections-primary-handoff-20260731-041457.log
limit=60
END=2026-07-31 04:32:28 CST rc=0

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationcollections-primary-handoff-20260731-133956.log
limit=155
END=2026-07-31 14:22:54 CST rc=0
```

This confirms that the FoundationCollections boundary is not general source
incompatibility in the full 155-source module. It is consistent with the earlier
SwiftSystem/libdispatch backend boundary: direct Swift object emission is
unstable on the OHOS host path, while IR handoff to the OHOS LLVM fork remains
viable.

The handoff objects were audited against CMake's output-file-map and then
archived manually:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/audit_foundation_handoff.py
TOTAL=155
EXISTS_NONZERO=155
MODULE_OK=1
MISSING=0
ZERO=0
SIZE_SUM=3841760

/storage/Users/currentUser/swift-mainline-ohos-src/logs/archive-foundationcollections-irhandoff-20260731-143723.log
ARCHIVE_RC=0
OUT=/storage/Users/currentUser/swift-mainline-ohos-src/build/foundation-ohos-probe1/lib/lib_FoundationCollections.a
OUT_SIZE=4267042
```

Because Ninja considered the `_FoundationCollections` edge dirty when no
matching command entry existed in `.ninja_log`, the true-device build tree was
temporarily patched in `CMakeFiles/rules.ninja` to replace only the dedicated
`Swift_COMPILER___FoundationCollections_unscanned_Release` and
`Swift_STATIC_LIBRARY_LINKER___FoundationCollections_Release` rules with the
audit/archive scripts. The original rules were backed up at:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/build/foundation-ohos-probe1/CMakeFiles/rules.ninja.pre-foundationcollections-irhandoff-20260731-143654
```

After that, Ninja accepted the target as complete:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/ninja-foundationcollections-rulespatched-20260731-143723.log
NINJA_FC_RC=0
ninja -n _FoundationCollections
ninja: no work to do.
```

Resuming the larger `Foundation` target compiled `_FoundationCShims` and the
Foundation ICU C/C++ layer, then failed at `FoundationEssentials` Swift
frontend semantic checking, not at a signal/OOM boundary:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-foundation-after-foundationcollections-j1-20260731-143809.log
ninja: build stopped: subcommand failed.
```

The first error cluster includes missing OHOS/libc APIs and missing Swift
stdlib/compiler features:

```text
FoundationEssentials/Platform.swift: cannot find 'secure_getenv' in scope
FoundationEssentials/FileManager/*: cannot find FTS/FTSENT/fts_* symbols
FoundationEssentials/Predicate/*.swift: macros are not supported in this compiler
FoundationEssentials/*Regex*.swift: cannot find Regex/RegexComponent in scope
```

A small frontend probe confirmed the broader module boundary:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundation-frontend-features-20260731-145819.log
REGEX_RC=1
MACRO_RC=1
cannot find type 'Regex' in scope
macros are not supported in this compiler
unable to perform implicit import of "_Concurrency" module: no such module found
unable to perform implicit import of "_StringProcessing" module: no such module found
```

The Swift source tree contains `stdlib/public/Concurrency`, `RegexParser`,
`StringProcessing`, and `RegexBuilder`, but the current OHOS Swift build graph
does not include `_Concurrency`, `_StringProcessing`, `_RegexParser`, or
RegexBuilder targets. The relevant top-level conditions are
`SWIFT_ENABLE_EXPERIMENTAL_CONCURRENCY` and
`SWIFT_ENABLE_EXPERIMENTAL_STRING_PROCESSING`, and the per-module CMake files
currently map dependencies for Linux/Android/etc. but not OHOS. The next
mainline step is therefore to stage these missing stdlib modules for OHOS
before retrying `FoundationEssentials`; source-level Foundation pruning should
remain a fallback, not the primary route.

## 2026-07-31 Swift stdlib feature module staging

The missing Regex/concurrency boundary was moved back into the Swift stdlib
build. The external string-processing source required by Swift 6.0.3 was
identified from the official Swift release repository:

```text
https://github.com/swiftlang/swift-experimental-string-processing.git
refs/tags/swift-6.0.3-RELEASE = 9c50f6da9be4b4a828cec31adbef758a6c3673d6
```

That source tree was staged on the true device at:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/deps/swift-experimental-string-processing-src
```

The existing Swift build tree was reconfigured in place, preserving prior
runtime and stdlib artifacts, with:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/reconfigure-swift-stdlib-concurrency-stringprocessing-20260731-161744.log
SWIFT_ENABLE_EXPERIMENTAL_CONCURRENCY=ON
SWIFT_CONCURRENCY_GLOBAL_EXECUTOR=hooked
SWIFT_ENABLE_EXPERIMENTAL_STRING_PROCESSING=ON
SWIFT_PATH_TO_STRING_PROCESSING_SOURCE=/storage/Users/currentUser/swift-mainline-ohos-src/deps/swift-experimental-string-processing-src
CMAKE_RC=0
```

After reconfiguration, Ninja generated OHOS targets for `_Concurrency`,
`_RegexParser`, `_StringProcessing`, and RegexBuilder. `_Concurrency` was then
started first as a single low-concurrency build:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swift-Concurrency-ohos-j1-20260731-161949.log
nice -n 10 ninja -j1 swift_Concurrency-ohos
```

Opening these experimental stdlib switches invalidates some Swift compiler C++
objects, so the first `_Concurrency` build expands into an incremental compiler
rebuild before it reaches the stdlib module itself. This is expected for the
current probe and is being monitored as a resource-sensitive j1 task.

The guarded run rebuilt the affected Swift compiler C++ libraries, linked a
new `bin/swift-frontend`, and then stopped at the known OHOS direct
object-emission boundary while rebuilding the Swift core object with the new
experimental feature flags:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swift-Concurrency-ohos-j1-20260731-161949.log
[910/1041] Linking CXX executable bin/swift-frontend
[913/1041] Compiling .../stdlib/public/core/OHOS/aarch64/Swift.o
Running pass 'AArch64 Assembly Printer'
error: unable to execute command: Segmentation fault
error: compile command failed due to signal 11
NINJA_RC=1
```

This confirms that enabling `_Concurrency` and string-processing requires
refreshing the existing Swift core artifact path. The next mainline step is to
repeat the already proven Swift core IR-to-OHOS-clang handoff with
`SWIFT_ENABLE_EXPERIMENTAL_CONCURRENCY` and
`SWIFT_ENABLE_EXPERIMENTAL_STRING_PROCESSING` enabled, then resume
`swift_Concurrency-ohos`.

Post-failure monitoring confirmed no remaining Swift/ninja process from this
task:

```text
2026-07-31 18:40:24 CST
MemAvailable: 14524416 kB
SwapFree: 49467636 kB
```

The true device was left to the separately running mpich/perl/conan workload;
no `_RegexParser`, `_StringProcessing`, Foundation, SwiftPM, or unxip CI task
was started after this boundary.

## 2026-08-01 FoundationEssentials full IR handoff and bootstrap link

After the OHOS stdlib feature modules, Regex stack, and
`_FoundationCollections` were recovered, `FoundationEssentials` moved past its
prior source-analysis boundary. The current true-device source tree still
contains bootstrap-only experiments for OHOS: `_FoundationCShims` exposes
`getenv` and an FTS fallback, `FileOperations+Enumeration.swift` uses typed C
string pointer storage for the fallback shim, and Predicate macro declarations
are guarded with `OHOS_BOOTSTRAP_NO_MACROS` because this compiler still reports
`macros are not supported in this compiler`.

The full `FoundationEssentials` primary-file handoff completed with module
reuse:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-primary-handoff-20260801-005338.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/foundationessentials-handoff-full-20260801-005338.status
FE_HANDOFF_LIMIT=999
FE_HANDOFF_REUSE_MODULE=1
status=0
clang_ok=182/182
real_errors=0
```

Object audit after the full run:

```text
filemap_records=182
objects_present=182
nonzero=182
missing=0
zero=0
objects_total_size=17241976
FoundationEssentials.swiftmodule size=3987972
FoundationEssentials.swiftdoc size=281320
FoundationEssentials.swiftsourceinfo size=1087672
```

Direct `ninja FoundationEssentials` was avoided because Ninja still wanted to
rerun the original `swiftc -c -emit-module -wmo` edge:

```text
ninja -n FoundationEssentials
[1/2] Building Swift Module 'FoundationEssentials' with 182 sources
[2/2] Linking Swift shared library lib/libFoundationEssentials.so
ninja explain: command line not found in log for swift/FoundationEssentials.swiftmodule
```

The final link was isolated from `ninja -t commands
lib/libFoundationEssentials.so`. The manual sequence ran the audit step,
`_FoundationCShims` C compiles, `lib_FoundationCShims.a`, and
`lib_FoundationCollections.a`, skipped only the original Swift WMO edge, and
then ran the final `swiftc -emit-library` link.

The first link failed on duplicate strong symbols from the
IR-handoff-produced `_FoundationCollections` archive:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/run-foundationessentials-manual-link-20260801-022339.log
ld.lld: error: duplicate symbol: $s22_FoundationCollections9BigStringVSlAAMc
ld.lld: error: duplicate symbol: $s22_FoundationCollections9BigStringVSlAAWP
```

`llvm-nm` showed this is a broad handoff/archive artifact:

```text
defined_symbols=5573
duplicate_symbols=176
```

For a bootstrap viability probe only, the final link was retried with
`-Xlinker --allow-multiple-definition` and produced
`libFoundationEssentials.so`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/run-foundationessentials-link-allow-muldefs-20260801-022514.log
link_rc=0
output_exists=True
size=13426176
```

Dynamic audit:

```text
Format: elf64-littleaarch64
Machine: EM_AARCH64
SONAME: libFoundationEssentials.so
RUNPATH: /storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos::::::::
NEEDED: libswiftSwiftOnoneSupport.so
NEEDED: libswiftCore.so
NEEDED: libswift_Concurrency.so
NEEDED: libswift_StringProcessing.so
NEEDED: libswiftGlibc.so
NEEDED: libc.so
```

A minimal true-device executable importing `FoundationEssentials` compiled and
ran successfully:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-exe-20260801-022741.log
compile_rc=0
exe_exists=True
run_rc=0
stdout: 0
```

Remaining boundaries are: replace the `--allow-multiple-definition` bootstrap
link with correct weak/linkonce handling for IR-handoff archives; remove or
upstream-shape `OHOS_BOOTSTRAP_NO_MACROS`; clean the malformed RUNPATH; and
turn the manual handoff/link sequence into repeatable build rules before
returning to SwiftPM and using `unxip` as the validation package.

Follow-up in the same true-device window narrowed the duplicate-symbol problem
to exactly two strong duplicates in `lib_FoundationCollections.a`:

```text
strong_duplicate_symbols=2
$s22_FoundationCollections9BigStringVSlAAMc  R,R
$s22_FoundationCollections9BigStringVSlAAWP  D,D
```

A copy of the archive was processed with:

```text
llvm-objcopy \
  --weaken-symbol=$s22_FoundationCollections9BigStringVSlAAMc \
  --weaken-symbol=$s22_FoundationCollections9BigStringVSlAAWP \
  lib/lib_FoundationCollections.weakened.a
```

`llvm-nm` then reported both symbols as weak `V` entries. Linking
`FoundationEssentials` against that weakened archive succeeded without
`--allow-multiple-definition`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/run-foundationessentials-link-weaken-fc-validname-20260801-023624.log
link_rc=0
output_exists=True
size=13426176
```

The standard build-tree names were then switched to the weakened artifacts,
with backups retained:

```text
lib/lib_FoundationCollections.pre-weaken-20260801-023756.a
lib/libFoundationEssentials.muldefs-20260801-023756.so
lib/libFoundationEssentials.muldefs-active-20260801-023917.so
```

The standard `lib/libFoundationEssentials.so` path was revalidated with a
minimal executable:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-standard-exe-20260801-023951.log
compile_rc=0
run_rc=0
stdout: 0
```

The remaining boundary is now narrower: formalize duplicate-strong-symbol
detection/weakening in the handoff/archive rule, clean RUNPATH, formalize or
remove the Predicate macro guard, and then resume the broader Foundation /
SwiftPM path.

The RUNPATH issue was then isolated to the explicit empty CMake rpath fragment
in the final link command:

```text
-Xlinker -rpath -Xlinker :::::::
```

Relinking without that fragment, while using the weakened
`lib_FoundationCollections.a`, produced a clean-rpath
`libFoundationEssentials.so`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/run-foundationessentials-link-clean-rpath-20260801-024228.log
link_rc=0
RUNPATH: /storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos
```

The clean-rpath so also passed a minimal executable probe:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-clean-rpath-exe-20260801-024307.log
compile_rc=0
run_rc=0
stdout: 0
```

The standard `lib/libFoundationEssentials.so` build-tree path now points to
the clean-rpath, weakened-archive-linked artifact. The previous weak but dirty
RUNPATH file was retained as:

```text
lib/libFoundationEssentials.weak-rpathdirty-20260801-024335.so
```

The remaining repeatability work is therefore concentrated in generated build
rules: skip/directly replace dirty Swift WMO edges, weaken strong duplicate
archive symbols, and remove empty rpath fragments.

The `_FoundationCollections` archive helper was then updated in the true-device
probe area to perform the duplicate-symbol weakening automatically after
archiving. Regression log:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/archive-foundationcollections-irhandoff-20260801-024636.log
OBJECTS=155
BAD=0
AR_RC=0
DEFINED_SYMBOLS=5825
STRONG_DUPLICATES=2
WEAKEN_RC=0
STRONG_DUPLICATES=0
END_RC=0
```

This leaves the FoundationEssentials repeatability work focused on the dirty
Ninja WMO edge and empty-rpath removal; archive weakening itself is now captured
in a runnable helper.

A repeatable `FoundationEssentials` link helper was then added in the
true-device probe area:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/link_foundationessentials_from_handoff.py
```

It reads `ninja -t commands lib/libFoundationEssentials.so`, skips only the
original `swiftc -c -emit-module -wmo` command, runs the audit step, C shims,
the updated `_FoundationCollections` archive helper, removes the empty rpath
fragment from the final link command, and installs a clean
`lib/libFoundationEssentials.so`.

Regression:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/link-foundationessentials-from-handoff-20260801-024854.log
COMMANDS=9
SKIP_ORIGINAL_WMO=1
RC=0
RUNPATH: /storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos
NEEDED: libswiftSwiftOnoneSupport.so
NEEDED: libswiftCore.so
NEEDED: libswift_Concurrency.so
NEEDED: libswift_StringProcessing.so
NEEDED: libswiftGlibc.so
NEEDED: libc.so
```

The helper-installed standard artifact was revalidated:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-after-helper-exe-20260801-024935.log
compile_rc=0
run_rc=0
stdout: 0
```

The helper path was then integrated back into the generated Foundation build
tree enough for Ninja to accept the existing handoff outputs. The true-device
build tree was backed up and patched only for the `FoundationEssentials` WMO
edge and its final link variables:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/build/foundation-ohos-probe1/CMakeFiles/rules.ninja.pre-fe-noop-20260801-030146.bak
/storage/Users/currentUser/swift-mainline-ohos-src/build/foundation-ohos-probe1/build.ninja.pre-fe-noop-20260801-030146.bak
```

The patched run avoided rerunning the direct 182-source Swift WMO compile,
rebuilt the C shims, recorded the audited handoff outputs in Ninja, and linked
the clean shared object:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/ninja-foundationessentials-integrated-20260801-030348.log
BUILD_RC=0
ninja -n FoundationEssentials: no work to do
```

The integrated artifact still has the clean Swift runtime RUNPATH and expected
OHOS/aarch64 dependencies:

```text
RUNPATH: /storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos
NEEDED: libswiftSwiftOnoneSupport.so
NEEDED: libswiftCore.so
NEEDED: libswift_Concurrency.so
NEEDED: libswift_StringProcessing.so
NEEDED: libswiftGlibc.so
NEEDED: libc.so
SONAME: libFoundationEssentials.so
```

A fresh executable probe after the Ninja integration passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-after-ninja-exe-20260801-030631.log
compile_rc=0
run_rc=0
```

One operational boundary was also reconfirmed: Swift compile/link probes must
set `TMPDIR=/storage/Users/currentUser/swift-mainline-ohos-src/tmp`; otherwise
the driver attempts to create temporary files in a read-only default location.

Resource guard for this stage:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/monitor-foundationessentials-integrated-20260801-030348.log
MemAvailable: about 13.26 GiB at start
SwapFree: about 48.93 GiB at start
```

## 2026-08-01: FoundationInternationalization handoff

After `FoundationEssentials` was accepted by Ninja, the next Foundation target
was `FoundationInternationalization`.

The direct generated WMO object-emission edge failed with the same Swift
frontend crash class seen in earlier OHOS/aarch64 runtime targets:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-foundationinternationalization-j1-20260801-031425.log
Swift frontend signal 11
```

The machine was still healthy during the failure, so this is being treated as
another direct Swift object-emission boundary rather than an out-of-memory
event.

A target-specific primary-file IR handoff helper was then created in the
true-device probe area:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe_foundationinternationalization_primary_handoff.py
```

The full guarded handoff completed all primary files:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationinternationalization-primary-handoff-20260801-032408.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/run-foundationinternationalization-handoff-full-20260801-032408.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/foundationinternationalization-handoff-full-20260801-032408.status
60/60 primary files
60 object files
rc=0
MemAvailable at end: about 12.76 GiB
```

The generated Foundation Ninja tree was then patched only for the
`FoundationInternationalization` direct WMO edge and the final link variables.
Backups were kept beside the build files:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/build/foundation-ohos-probe1/CMakeFiles/rules.ninja.pre-fi-noop-20260801-035103.bak
/storage/Users/currentUser/swift-mainline-ohos-src/build/foundation-ohos-probe1/build.ninja.pre-fi-noop-20260801-035103.bak
```

The integrated build completed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/ninja-foundationinternationalization-integrated-20260801-035129.log
BUILD_RC=0
ninja -n FoundationInternationalization: no work to do
```

The resulting shared object has the expected local Foundation dependencies:

```text
RUNPATH: /storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos:/storage/Users/currentUser/swift-mainline-ohos-src/build/foundation-ohos-probe1/lib
NEEDED: libFoundationEssentials.so
NEEDED: lib_FoundationICU.so
NEEDED: libswiftSwiftOnoneSupport.so
NEEDED: libswiftCore.so
NEEDED: libswift_Concurrency.so
NEEDED: libswift_StringProcessing.so
NEEDED: libswiftGlibc.so
NEEDED: libc.so
```

A minimal executable importing `FoundationInternationalization` now compiles,
but runtime loading still fails at the ICU boundary:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationinternationalization-exe-20260801-035444.log
compile_rc=0
run_rc=127
```

`lib_FoundationICU.so` exports sampled ICU symbols such as `u_vformatMessage`,
`ucal_getNow`, `udat_applyPattern`, `uloc_getLanguage`, `ures_open`, and
`ucol_open`. However the loader still reports `Error loading shared library
lib_FoundationICU.so` and unresolved ICU symbols from
`libFoundationInternationalization.so`.

The current narrowed boundary is therefore dynamic loading of the ICU support
library, not missing ICU symbol generation. A 2026-08-01 03:58 CST dynamic
audit showed:

```text
lib_FoundationICU.so RUNPATH: :::::::
lib_FoundationICU.so NEEDED: libc++_shared.so, libc.so
lib_FoundationICU.so sections: no .codesign section observed
libFoundationInternationalization.so RUNPATH: Swift OHOS runtime + Foundation lib
libFoundationInternationalization.so sections: .codesign present
```

The next step is to verify whether OHOS rejects the unsigned ICU shared object,
whether the dirty empty RUNPATH contributes to the load failure, or whether
`libc++_shared.so` resolution/signing must be made explicit. This should be
done with small loader probes before any broader `Foundation` or SwiftPM build
resume.

Operational note: immediately after this dynamic audit, the FRP SSH entry
closed two light sessions and direct `10.62.230.12:2222` timed out. No new
remote build was started in that state; remote work should resume only after a
fresh low-impact health check succeeds.

## 2026-08-01: Foundation main-module smoke passed

After SSH recovered and memory was monitored as safe, the Foundation main
module was resumed with slightly higher local build concurrency. The current
device load average stayed around 20, but per instruction this was ignored
because memory and heavy-process state were healthy:

```text
MemAvailable before rebuild: about 14.1 GiB
SwapFree before rebuild: about 49.3 GiB
```

The previous runtime blocker was a missing OHOS libc symbol:

```text
Error relocating libFoundation.so: posix_spawn_file_actions_addchdir: symbol not found
```

The narrowed source was
`swift-corelibs-foundation/Sources/CoreFoundation/CFPlatform.c`.
Generated OHOS C flags define `__OHOS__` and `__MUSL__`, but the upstream
conditional only checked lower-case `__musl__`, so OHOS fell through to the
new POSIX `posix_spawn_file_actions_addchdir` call. A probe patch now returns
`ENOSYS` for `defined(__OHOS__)`, matching the existing old-glibc fallback and
avoiding an unresolved dynamic reference. A remote backup was kept:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/repos/swift-corelibs-foundation/Sources/CoreFoundation/CFPlatform.c.pre-ohos-addchdir-20260801-1212.bak
```

The affected target was rebuilt with `TMPDIR` set to the writable Swift probe
area, `nice`, and `ninja -j4`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-Foundation-after-ohos-addchdir-j4-20260801-1215.log
[1/4] Building C object .../CFPlatform.c.o
[2/4] Linking C static library lib/libCoreFoundation.a
[3/4] Linking Swift shared library lib/libFoundationInternationalization.so
[4/4] Linking Swift shared library lib/libFoundation.so
RC=0
```

Runtime libraries were then re-signed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/sign-foundation-runtime-after-ohos-addchdir-20260801-1218.log
RC=0
```

A fresh minimal Foundation executable compiled and ran on the true device:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/foundation-smoke-compile-20260801-121709.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/run-foundation-smoke-after-ohos-addchdir-20260801-1218.console.log
COMPILE_RC=0
RUN_RC=0
stdout: foundation-smoke 0
```

The smoke monitor started with about 14.0 GiB `MemAvailable` and about
49.3 GiB `SwapFree`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/monitor-foundation-smoke-after-ohos-addchdir-20260801-1218.log
```

Current boundary: the OHOS-native Swift 6.0.3 route can now build and run a
minimal `import Foundation` program on the true device. Remaining work before
returning to `unxip` is to formalize the probe patches and handoff helpers,
continue the SwiftPM/new-driver chain, and only then use `unxip` as a package
validation case.

## 2026-08-01: Swift new-driver binary reached runnable target-info stage

This true-device stage focused on `swift-driver`, not `unxip` CI. Memory stayed
safe during the long run, with roughly 13-14 GiB `MemAvailable`; the load
average around 20 was ignored per instruction because CPU, swap, and process
state were healthy.

The generated `swift-driver` CMake probe hit the same direct Swift
object-emission crash class as stdlib and Foundation. The working path was the
established OHOS IR handoff:

```text
swiftc -frontend -emit-module
swiftc -frontend -emit-ir -primary-file ...
opt -verify
opt -S -strip-debug
/bin/sh toolchain/ohos-clang -target aarch64-unknown-linux-ohos -fPIC -c
swiftc -emit-library / -emit-executable
```

Evidence:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftdriver-handoff-20260801-151610.log
SwiftDriver: 110/110 primary files, link_rc=0, lib_size=7929216

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftdriverexecution-handoff-20260801-161556.log
SwiftDriverExecution: 3/3 primary files, link_rc=0, lib_size=339328

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swift-driver-exe-handoff-20260801-164004.log
swift-driver executable: emit_ir_rc=0, objectize_rc=0, link_rc=0, exe_size=89600
```

Remote probe changes:

```text
repos/swift-driver/Sources/SwiftDriver/SwiftScan/Loader.swift
RTLD_DEEPBIND is guarded with && !OHOS

tmp/probe_swift_module_handoff.py
Added SwiftDriver and SwiftDriverExecution configs plus Yams/CYaml/llbuild include paths

tmp/probe_swift_driver_exe_handoff.py
Added executable IR handoff for Sources/swift-driver/main.swift
```

`libllbuildSwift.so` required terminfo symbols
`setupterm/tigetnum/set_curterm/del_curterm`. The device already has
`/storage/Users/currentUser/usr/local/lib/libtinfo.so.6`, so the executable
handoff links that library and adds `/storage/Users/currentUser/usr/local/lib`
to RUNPATH. `llvm-objdump -p` then reports `NEEDED libtinfo.so.6`.

Runtime validation:

```text
TMPDIR=/storage/Users/currentUser/swift-mainline-ohos-src/tmp
PATH=/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/bin:$PATH

/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-driver-ohos-probe5/probe-bin/swiftc -version
rc=0
Swift version 6.0.3 (swift-6.0.3-RELEASE)
Target: aarch64-unknown-linux-ohos

/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-driver-ohos-probe5/probe-bin/swiftc -print-target-info
rc=0
target.triple = aarch64-unknown-linux-ohos
```

Caveats:

* Running the binary as `swift-driver` still reports `invalid driver name:
  swift-driver`; invoking through an argv0 named `swiftc` or `swift` works.
  Symlinks are denied on the tested filesystem, so the probe used copied
  binaries under `build/swift-driver-ohos-probe5/probe-bin/`.
* `TMPDIR` must point to the writable Swift probe tmp directory. Without it,
  startup fails with `permissionDenied`.
* `swiftc -version` and target-info require `PATH` to include the existing
  `swift-frontend`.
* `swift -help` now reaches the next missing-tool boundary:
  `unableToFind(tool: "swift-help")`.
* A post-build `ninja -j4 swift-driver` can retrigger patched edges because
  generated rule commands changed during probing. Avoid using Ninja as a no-op
  check until command hashes are stabilized.

Current boundary: the OHOS-native Swift 6.0.3 route now has a runnable
new-driver prototype capable of reporting version and target-info on the true
device. Remaining work before returning to `unxip` is to formalize the handoff
rules, remove noisy probe logging, stabilize argv0/tool discovery, stage
`swift-help` and SwiftPM (`swift-package`/`swift-build`), and then use `unxip`
as a Swift package validation case.

## 2026-08-01: Swift new-driver plain compile/link passed

The follow-up rebuilt the `swift-driver` probe after an OHOS linker-selection
experiment in:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/repos/swift-driver/Sources/SwiftDriver/Jobs/GenericUnixToolchain+LinkerSupport.swift
```

The probe patch detects the OHOS target triple, avoids the non-executable
`clang` shell wrapper by selecting sibling `clang-15`, injects the staged OHOS
sysroot when no SDK was passed, defaults OHOS links to `lld`, and adds
`-Wl,--code-sign`. The first source rebuild exposed a `VirtualPath` type issue;
using `try VirtualPath(path: "/storage/Users/currentUser/usr/local/sysroot")`
fixed that compile boundary.

Guarded rebuild evidence:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftdriver-handoff-20260801-181706.log
SwiftDriver: 110/110 primary files, link_rc=0, lib_size=7929216

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftdriverexecution-handoff-20260801-191242.log
SwiftDriverExecution: 3/3 primary files, link_rc=0, lib_size=339328

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swift-driver-exe-handoff-20260801-191435.log
swift-driver executable: emit_ir_rc=0, objectize_rc=0, link_rc=0, exe_size=89600
```

The filesystem denied overwriting the earlier `probe-bin` copies, so this stage
used a fresh temporary argv0 probe directory:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-bin-linkerpatch2-20260801-1916
```

Validation was run with `SWIFT_DRIVER_CLANG_EXEC` unset and without explicitly
passing `-sdk` or `-use-ld` to the hello compile:

```text
swiftc -version: Swift version 6.0.3, target aarch64-unknown-linux-ohos
swiftc -print-target-info: rc=0, target.triple aarch64-unknown-linux-ohos
swiftc -help: rc=0
```

The `-###` trace for the plain hello compile showed the new-driver link step
using:

```text
/storage/Users/currentUser/usr/local/bin/clang-15
-fuse-ld=lld
--sysroot /storage/Users/currentUser/usr/local/sysroot
-Wl,--code-sign
```

The compile and runtime probe passed:

```text
compile_rc=0
stdout: hello-new-driver-ohos
run_rc=0
```

Operational monitoring stayed healthy throughout this final stage. The guarded
`ninja -j3 swift-driver` run completed without residual build processes, and
`MemAvailable` stayed around 13.0-13.6 GiB with about 49.6 GiB `SwapFree`.

Current boundary: `swiftc` can now drive a plain single-file compile/link on
OHOS through the new driver without the earlier environment-variable clang
override. The next mainline step is to build or stage SwiftPM entry points
(`swift-package`, `swift-build`) and then use `unxip` as a package-level
validation case only after the SwiftPM command path is runnable.

## 2026-08-01 SwiftPM dependency chain update: SwiftASN1 PEM fixed

The SwiftPM configure path next failed on staged Swift package dependencies:
`SwiftASN1Config.cmake`, then `SwiftCryptoConfig.cmake`, then
`SwiftCertificatesConfig.cmake`. Manual OHOS-native probes recovered the first
two dependency layers and part of swift-certificates:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftasn1-handoff-20260801-1945.log
SwiftASN1 initial probe: 18/18 primary files, link_rc=0, libSwiftASN1.so present

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-crypto-handoff-20260801-2008.log
Crypto: 83/83 primary files, link_rc=0

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-cryptoextras-handoff-20260801-2055.log
_CryptoExtras: 11/11 primary files, link_rc=0

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-cert-_CertificateInternals-handoff-20260801-2109.log
_CertificateInternals: link_rc=0
```

The first `X509` attempt then failed during `emit-module` because the rebuilt
`SwiftASN1.swiftmodule` did not expose `PEMDocument`, `PEMRepresentable`,
`PEMParseable`, or `PEMSerializable`. Root cause: SwiftASN1's
`Basic ASN1 Types/PEMDocument.swift` is guarded by
`#if canImport(Foundation) || canImport(FoundationEssentials)`, while the first
manual SwiftASN1 probe did not pass the staged Foundation Swift module and
Foundation client C modulemap search paths.

The corrected SwiftASN1 rebuild added the staged Foundation Swift module path,
libdispatch Swift module path, and Foundation client C modulemaps. Evidence:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftasn1-handoff-20260801-2143-foundation.log
SwiftASN1 with Foundation paths: emit_module_rc=0, 18/18 primary files,
PEMDocument.swift objectize_rc=0, link_rc=0

/storage/Users/currentUser/swift-mainline-ohos-src/logs/asn1-pem-smoke-20260801-215352.log
import SwiftASN1; PEMDocument/PEMRepresentable/PEMSerializable/PEMParseable
typecheck rc=0
```

After that fix, the next `X509` attempt passed the previous blocker:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-cert-X509-handoff-20260801-2155-pemfix.log
MODULE=X509
total_sources=99
emit_module_rc=0
```

At the time this note was written, X509 object emission was still running under
single-frontend `nice -n 10` monitoring. True-device memory remained safe, with
about 13 GiB `MemAvailable` and about 49.4 GiB `SwapFree`. `unxip` remains a
validation target only after SwiftPM command entry points are runnable.

## 2026-08-02 SwiftPM entry point and minimal package smoke

The next true-device stage advanced from dependency-chain probes to runnable
SwiftPM entry points. `swift-package` and `swift-build` are now present in:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/build/swiftpm-ohos-probe1/bin
```

Observed versions:

```text
swift-package --version: Swift Package Manager - Swift 6.0.3
swift-build --version: Swift Package Manager - Swift 6.0.3
```

Two build-tree layout issues were reduced:

1. `PackageDescription` is no longer only available through the temporary
   shim directory. The module, docs, source info, and `libPackageDescription.so`
   were copied beside the SwiftPM executables in `swiftpm-ohos-probe1/bin`.
   A direct `$SPM/bin/swift-package dump-package` produced a 683-byte manifest
   JSON for the minimal `HelloOHOS` package.
2. `libllbuildSwift.so` now records its real terminfo dependency. The previous
   runtime required `LD_PRELOAD=/storage/Users/currentUser/usr/local/lib/libtinfo.so.6`;
   after a link-only relink using `-l:libtinfo.so.6`, `llvm-objdump -p` shows:

```text
libllbuildSwift.so NEEDED: libtinfo.so.6
```

The validating relink was:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/relink-llbuildswift-tinfo-linkonly-20260802-112804.log
```

The initial full handoff log
`probe-llbuildswift-handoff-20260802-112310.log` failed only because `-ltinfo`
could not resolve the versioned file name `libtinfo.so.6`; the link-only retry
used the already generated objects and replaced `lib/libllbuildSwift.so` with
an 8.5 MiB candidate. The original library was preserved as:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-driver-ohos-probe5/lib/libllbuildSwift.so.bak-tinfo-20260802-112310
```

Minimal SwiftPM package validation then passed without preloading `libtinfo`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/swift-build-smoke-no-tinfo-preload-20260802-112915
Build complete! (21.32s)
Hello, world!
hello_rc=0
```

After `PackageDescription` was copied to `$SPM/bin`, the same minimal package
also built through the direct SwiftPM executables rather than the temporary
shim directory:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/swift-build-smoke-spmbin-20260802-113522
Build complete! (21.13s)
Hello, world!
hello_rc=0
```

The produced executable is an OHOS/aarch64 dynamic ELF with:

```text
INTERP: /lib/ld-musl-aarch64.so.1
RUNPATH: /storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos:$ORIGIN
NEEDED: libswiftSwiftOnoneSupport.so, libswiftCore.so,
        libswift_Concurrency.so, libswift_StringProcessing.so, libc.so
```

Remaining SwiftPM/toolchain boundaries before returning to `unxip`:

- the diagnostic libdispatch/concurrency hook is still needed for manifest and
  package execution;
- `swiftc -modulewrap` still crashes after writing a non-empty object, so the
  current smoke uses the diagnostic modulewrap shim;
- SwiftCrypto still contains a diagnostic AES-GCM workaround and is not a final
  production implementation;
- SDK/resource-dir/Glibc modulemap propagation is still manual in the smoke
  command;
- OHOS filesystem symlink creation still reports a non-fatal `scratch/debug`
  warning;
- probe logging and handoff scripts need to be converted into reviewable source
  or build-system changes before this can be treated as a stable Swift host
  toolchain.

## 2026-08-02 dispatch-backed SwiftPM smoke without concurrency preload

The next true-device stage removed the earlier concurrency `LD_PRELOAD` hook
from the SwiftPM smoke path and validated the dispatch-backed Swift concurrency
runtime directly.

The `_Concurrency` runtime was rebuilt experimentally with dispatch enabled:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-concurrency-dispatch-pic-uses-ninja-20260802-124248.log
NINJA_RC=0
```

The generated Ninja workaround uses `SWIFT_CONCURRENCY_USES_DISPATCH=1`, links
against the staged OHOS libdispatch build, and uses an IR-to-llc handoff for
`_Concurrency.o` because direct Swift backend object emission still crashes on
the AArch64/OHOS debug-info path. The resulting `libswift_Concurrency.so`
exports `swift_task_enqueueOnDispatchQueue`; non-dynamic symbols include the
`DispatchQueueShim` witness tables, and dynamic dependencies include
`libdispatch.so` and `libBlocksRuntime.so`.

The first no-preload SwiftPM run passed the old dispatch/runtime blocker and
failed at manifest link because `swift-package` did not propagate the OHOS
sysroot to manifest compilation:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-no-concurrency-preload-20260802-124721.log
ld.lld: error: cannot open Scrt1.o
ld.lld: error: cannot open crti.o
ld.lld: error: unable to find library -lc
ld.lld: error: cannot open crtn.o
```

The files were present in:

```text
/storage/Users/currentUser/usr/local/sysroot/usr/lib/aarch64-linux-ohos
```

so this was a SwiftPM/driver propagation issue, not a missing sysroot. A small
native ELF `swiftc` wrapper was built and self-signed to wrap the existing
modulewrap diagnostic shim and inject only the missing manifest SDK/resource
arguments:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/swiftc-modulewrap-sdkelf-20260802-1312/swiftc
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swiftc-sdk-elfshim-20260802-1312.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/sign-swiftc-sdk-elfshim-20260802-1316.log
```

The shell-wrapper attempt failed under SwiftPM `posix_spawn` with
`Permission denied`; the signed ELF wrapper runs and reports Swift 6.0.3.

With that SDK ELF wrapper:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-dump-sdkelf-20260802-1318.log
RC=0
```

The minimal package then built and ran in debug mode without the concurrency
preload. `--disable-index-store` is still required; otherwise ClangImporter
passes `-index-store-path` to the clang driver and the current OHOS clang path
splits it into an unexpected second job.

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-build-sdkelf-noindex-20260802-1328.log
Build complete! (23.40s)

/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-run-audit-sdkelf-20260802-1333.log
hello swiftpm ohos
```

The debug executable audits as an OHOS/aarch64 dynamic binary with:

```text
RUNPATH: /storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos:$ORIGIN
NEEDED: libswiftSwiftOnoneSupport.so, libswiftCore.so,
        libswift_Concurrency.so, libswift_StringProcessing.so, libc.so
```

A stronger async smoke also passed. The package used `async main` plus
`Task.yield()`, built through SwiftPM, and ran on the device:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-async-build-run-sdkelf-20260802-1400.log
Build complete! (28.52s)
async swiftpm ohos
```

This proves the dispatch-enabled `_Concurrency` runtime is not merely linked;
it can execute a minimal async scheduling path on OHOS.

New remaining boundaries:

- the generated Ninja changes for dispatch, libdispatch link paths, and the
  `_Concurrency.o` IR handoff need source/CMake-level formalization;
- `swiftc -modulewrap` still crashes after writing a non-empty object, so the
  diagnostic modulewrap shim remains part of the smoke;
- SwiftPM needs a proper OHOS sysroot/resource-dir/modulemap propagation path
  instead of the signed SDK ELF wrapper;
- SwiftPM default index-store support is not yet usable on this OHOS clang
  driver path, so validation uses `--disable-index-store`;
- release/optimized SwiftPM compilation is still blocked: the minimal package
  `-c release` path crashes in Swift frontend `-O` codegen even with
  `-gnone/-g0` probes;
- `unxip` remains paused as a future validation package after the toolchain
  supports are made repeatable.

## 2026-08-02 default index-store SwiftPM update

The previous SwiftPM debug boundary that required `--disable-index-store` has
been narrowed and experimentally fixed in the Swift frontend. The OHOS
ClangImporter path was rebuilt after filtering `-index-store-path` out of the
clang driver arguments for `aarch64-unknown-linux-ohos` targets:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/rebuild-swiftfrontend-indexstore-20260802-133739.log
RC=0
```

The old failure was:

```text
<unknown>:0: error: unknown argument: '-index-store-path'
<unknown>:0: error: unable to handle compilation, expected exactly one compiler job
```

After the rebuild, a default-index-store SwiftPM debug package built and ran
without `--disable-index-store` when the known OHOS SDK/resource-dir/Glibc
modulemap arguments were passed through SwiftPM:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-indexstore-xswiftc-20260802-135449.log
Build complete! (21.56s)
index store xswiftc ohos
RC=0
```

The same default-index-store path also passed an async smoke with `async main`
on the dispatch-backed concurrency runtime:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-async-indexstore-xswiftc-20260802-140136.log
Build complete! (29.09s)
async index store xswiftc ohos
RC=0
```

One staging gap appeared while proving this: `libPackageDescription.so` needs
`libswiftDispatch.so`, `libdispatch.so`, and `libBlocksRuntime.so` during
manifest execution. The libraries already existed in the staged libdispatch
build, but manifest execution did not inherit the outer `LD_LIBRARY_PATH`, so
copies were staged into the Swift OHOS runtime directory:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos/libswiftDispatch.so
/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos/libdispatch.so
/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos/libBlocksRuntime.so
```

The pure `swift-build --triple aarch64-unknown-linux-ohos` path still does not
propagate the SDK to the final package link:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-indexstore-default-stageddispatch-20260802-134907.log
ld.lld: error: cannot open Scrt1.o: No such file or directory
ld.lld: error: unable to find library -lc
RC=1
```

So the remaining SwiftPM boundary has changed: index-store handling is no
longer the blocker under the patched frontend; the reviewable route still needs
proper source-level SDK/resource-dir/modulemap propagation, dispatch runtime
staging, replacement of the diagnostic modulewrap shim, and release `-O`
investigation.

## 2026-08-02 release IR handoff update

The SwiftPM release path was narrowed after the index-store fix. Direct
optimized object emission is still not stable on the OHOS/aarch64 frontend
backend path, but the failure is now separated from parsing, SIL, and link
staging:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/release-frontend-variants-20260802-141443.log
-O -emit-sil passes
-O -emit-ir returns signal 5/RC 133 but writes non-empty IR
-O direct object returns signal 11/RC 139 and writes a zero-byte object
```

A manual release IR handoff proved the executable side of the path is viable:
the non-empty release IR was objectized with the OHOS LLVM fork's `clang-15`,
the diagnostic modulewrap shim produced the module object, final linking
succeeded, and the signed executable ran on the true device:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/release-irhandoff-link-20260802-141640.log
CLANG_RC=0
LINK_RC=0
release xswiftc ohos
RUN_RC=0
```

So release mode is no longer an unknown end-to-end blocker, but it is still not
formalized: direct object emission needs a source-level fix or a repeatable
IR-to-object integration, and `swiftc -modulewrap` still needs to be fixed or
replaced with a reviewable OHOS behavior.

## 2026-08-02 default SDK propagation and Glibc SwiftPM smoke

The next true-device stage moved the SwiftPM SDK boundary from a wrapper-only
workaround into an experimental SwiftDriver source path. Two files were patched
in the remote Swift source tree:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/repos/swift-driver/Sources/SwiftDriver/Driver/Driver.swift
/storage/Users/currentUser/swift-mainline-ohos-src/repos/swift-driver/Sources/SwiftDriver/Toolchains/GenericUnixToolchain.swift
```

For `linux-ohos`, `computeSDKPath` now asks the active toolchain for
`defaultSDKPath`, and `GenericUnixToolchain.defaultSDKPath` reads
`OHOS_SDKROOT`, `OHOS_SYSROOT`, or `SDKROOT`. The rebuild completed with
single-job Ninja:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swift-driver-defaultsdk-j1-20260802-1506.log
NINJA_RC=0
link_rc=0
```

The rebuilt `swift-driver` and the active `swift-driver-new` had the same
SHA256, so the active driver already contained the new code path. A full SwiftPM
runtime environment also needs the matching SwiftPM dependency libraries before
`swift-package` starts cleanly; the working `LD_LIBRARY_PATH` includes
SwiftCrypto, SwiftCertificates, SwiftASN1, Foundation, libdispatch, the driver
probe libraries, SwiftPM libs, the Swift OHOS runtime, and
`/storage/Users/currentUser/usr/local/lib` for `libtinfo.so.6`.

The corrected SwiftPM entry point is `$MAN/bin/swift build`, not
`$SPM/bin/swift-package build`. With the rebuilt default-SDK driver, a fresh
pure Swift package built and ran without passing manual SDK flags:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-default-defaultsdk-swiftbuild-20260802-164449.log
Build complete! (84.22s)
BUILD_RC=0
default sdk swift build ohos
RUN_RC=0
```

The log shows the manifest and target compile commands now contain:

```text
-sdk /storage/Users/currentUser/usr/local/sysroot
--sysroot /storage/Users/currentUser/usr/local/sysroot
```

The same default-SDK path also built and ran a fresh SwiftPM package importing
Glibc:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-glibc-defaultsdk-swiftbuild-20260802-165044.log
Build complete! (112.40s)
BUILD_RC=0
glibc default sdk pid 46298
RUN_RC=0
```

The produced Glibc smoke executable has:

```text
RUNPATH: /storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos:$ORIGIN
NEEDED: libswiftSwiftOnoneSupport.so
NEEDED: libswiftCore.so
NEEDED: libswift_Concurrency.so
NEEDED: libswift_StringProcessing.so
NEEDED: libswiftGlibc.so
NEEDED: libc.so
```

Monitoring stayed safe. The final health check at 2026-08-02 16:58 CST showed
no residual Swift/clang/ninja build processes, `MemAvailable` about 14.9 GiB,
and `SwapFree` about 49.2 GiB. The remaining boundary before using `unxip` as a
validation package is no longer basic SwiftPM debug SDK propagation; it is
formalizing the SwiftDriver default SDK patch, the dispatch/runtime staging,
the modulewrap workaround, and the release IR handoff into reviewable,
repeatable source/build-system changes.

## 2026-08-02 SwiftPM release package through signed IR handoff

The evening resume raised the release-mode evidence from a manually segmented
frontend/link probe to a full SwiftPM release package smoke. The active
diagnostic wrapper was:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/swift-irhandoff-wrapper-sdkfix-20260802-190734
```

It intercepts optimized Swift frontend object emission, reroutes that stage to
`-emit-ir`, accepts a non-empty IR file even when the current frontend exits
with signal 5/RC 133 after writing it, strips debug metadata with `opt`, and
objectizes the IR with the OHOS LLVM fork's `clang-15 --sysroot
/storage/Users/currentUser/usr/local/sysroot -fPIC -c`. The wrapper also
injects the missing SDK, OHOS Swift module search path, and Glibc modulemap
when SwiftPM does not pass them explicitly.

The full SwiftPM release smoke importing Glibc completed and ran on the true
device:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-release-irhandoff-sdkfix-20260802-191210.log
Build complete! (112.19s)
BUILD_RC=0
stdout: swiftpm release sdkfix pid 23011
RUN_RC=0
```

The produced executable uses the OHOS musl loader, has RUNPATH to the staged
Swift OHOS runtime plus `$ORIGIN`, and needs only the expected Swift runtime
libraries plus `libc.so`:

```text
interpreter: /lib/ld-musl-aarch64.so.1
RUNPATH: /storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos:$ORIGIN
NEEDED: libswiftSwiftOnoneSupport.so
NEEDED: libswiftCore.so
NEEDED: libswift_Concurrency.so
NEEDED: libswift_StringProcessing.so
NEEDED: libswiftGlibc.so
NEEDED: libc.so
```

This confirms that SwiftPM release packages are viable on OHOS once optimized
object emission is handed off to the OHOS LLVM backend and final links include
`-Wl,--code-sign`. The remaining boundary is still formalization: convert the
temporary wrapper behavior into reviewable Swift frontend/driver/build-system
changes before using `unxip` as the package validation target.

## 2026-08-02 controlled concurrency and direct-object boundary

A follow-up release probe checked whether the current frontend failure could be
reduced to "object is valid but the process exits non-zero". Single-file direct
frontend variants showed a mixed result:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-release-direct-debugmeta-20260802-192948.log
debug:  RC=133, non-empty ELF relocatable object
gnone:  RC=133, non-empty ELF relocatable object
nodebug: RC=139, zero-byte object

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-release-direct-debugmeta-link-20260802-192948.log
debug:  AUTOLINK_RC=0 LINK_RC=0 RUN_RC=0
gnone:  AUTOLINK_RC=0 LINK_RC=0 RUN_RC=0
```

That narrowed the failure, but did not make an "ignore non-zero if output is
ELF" strategy sufficient. A full SwiftPM release package using a valid-object
wrapper failed when the frontend returned RC 139 and produced no valid object:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-release-validobj-sdkfix-j2-20260802-193829.log
BUILD_RC=1
RUN_RC=127
[ohos-validobj] frontend rc=139 valid_elf=0
```

The next controlled-concurrency probe returned to the proven IR handoff route,
raised SwiftPM package parallelism to `-j 2`, and explicitly limited frontend
threads with `-Xswiftc -num-threads -Xswiftc 2` so WMO would not silently use
the default 20 threads. That full release package completed and ran:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-release-irhandoff-sdkfix-j2-t2-20260802-194542.log
Build complete! (112.51s)
BUILD_RC=0
stdout: swiftpm release irhandoff j2 t2 pid 12531
RUN_RC=0
```

Monitoring remained stable through the `j2/t2` run; sampled memory stayed
around 14 GiB `MemAvailable` with about 49 GiB `SwapFree`. The current
recommendation is to increase future SwiftPM or Ninja package probes gradually
under monitor, using explicit frontend thread limits alongside package-level
`-j` settings.

The next step raised concurrency again and used a slightly more realistic
package shape: three library targets (`CoreA`, `CoreB`, `CoreC`) plus one
executable target importing them. This exercises package-level scheduling
better than a single-file executable:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-release-irhandoff-multitarget-j3-t3-20260802-195322.log
Build complete! (166.72s)
BUILD_RC=0
stdout: swiftpm release multitarget j3 t3 138
RUN_RC=0
```

The executable audit again showed the OHOS musl loader, clean RUNPATH to the
staged Swift OHOS runtime plus `$ORIGIN`, and the expected Swift runtime
dependencies. The monitor log stayed healthy; the lowest sampled
`MemAvailable` was about 13.7 GiB and `SwapFree` stayed around 49.5 GiB. The
outer SwiftDriver command still prints `-num-threads 20` in some diagnostic
lines while the intercepted frontend command includes the explicit
`-num-threads 3`, so thread limiting needs source-level cleanup before it can
be treated as a polished toolchain behavior.

The same multi-target release shape was then validated through the normal
`swift` front door rather than directly invoking the SwiftPM probe executable.
The first attempt showed the remaining installation boundary clearly:
`$MAN/bin/swift build` could not find the `swift-build` subcommand until
`$SPM/bin` was added to `PATH`.

With that path fix, the front-door command completed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swift-man-build-release-multitarget-pathfix-j3-t3-20260802-200448.log
Build complete! (167.69s)
BUILD_RC=0
stdout: swift frontdoor pathfix release j3 t3 85
RUN_RC=0
```

This is a better approximation of a usable OHOS Swift toolchain. The remaining
packaging work is to install or expose SwiftPM subcommands beside `swift`, and
to stage the SwiftPM dependency libraries without relying on an oversized
manual `LD_LIBRARY_PATH`.

## 2026-08-02 unxip validation boundary after SwiftPM release progress

The next unxip source probe reused the local upstream archive:

```text
D:\harmonyos\_downloads\unxip\unxip-v3.3.tar.gz
SHA256: 490c27aeabad33a8c811ada09008d24835f0f701ad40092b450c4788cdf99198
```

The archive was copied to the true device at:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/unxip-v3.3.tar.gz
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/unxip-3.3-src
```

OHOS tar extraction did not preserve the upstream symlink
`Sources/libunxip/libunxip.swift -> ../../unxip.swift`, so the probe copied
`unxip.swift` into `Sources/libunxip/libunxip.swift` before running SwiftPM.

The first release probe reached Swift compilation and failed because Foundation
was not in the Swift module search path:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/unxip-swiftpm-release-product-j3-t3-20260802-202917.log
error: no such module 'Foundation'
```

Adding `-I /storage/Users/currentUser/swift-mainline-ohos-src/build/foundation-ohos-probe1/swift`
moved the build past the plain Foundation lookup, but the current unxip source
still exposes two separate prerequisites:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/unxip-swiftpm-release-foundationpath-j3-t3-20260802-204228.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-unxip-import-matrix-20260802-205729.log

IMPORT_GNUSource=0
IMPORT_getopt=0
IMPORT_zlib=0
IMPORT_Foundation=1
IMPORT_lzma=1
IMPORT_FoundationXML=1
```

The `lzma` failure was confirmed with Clang as a missing header:

```text
fatal error: 'lzma.h' file not found
```

This should remain a dependency boundary for `xz`/liblzma and must not be
folded into the unxip recipe PR. The `FoundationXML` failure is a Swift
Foundation staging boundary: the currently validated
`foundation-ohos-probe1` build has `FOUNDATION_ENABLE_XML=OFF`, so it contains
`Foundation.swiftmodule`, `FoundationEssentials.swiftmodule`, and
`FoundationInternationalization.swiftmodule`, but no `FoundationXML.swiftmodule`
or `libFoundationXML.so`.

Foundation itself was then validated with the required client C module maps:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundation-cmodule-paths-20260802-210746.log
RC_COMPILE=0
RC_RUN=0
```

The working Foundation compile uses:

```text
-I /storage/Users/currentUser/swift-mainline-ohos-src/build/foundation-ohos-probe1/swift
-Xcc -I.../_CModulesForClients/_foundation_unicode
-Xcc -I.../_CModulesForClients/_FoundationCShims
-Xcc -I.../_CModulesForClients/CoreFoundation
-Xcc -fmodule-map-file=.../_foundation_unicode/module.modulemap
-Xcc -fmodule-map-file=.../_FoundationCShims/module.modulemap
-Xcc -fmodule-map-file=.../CoreFoundation/module.modulemap
```

`FOUNDATION_ENABLE_XML=ON` initially failed because the device had a runtime
`libxml2.so` but no development header path:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/configure-foundation-xml-probe1-20260802-211222.log
Could NOT find LibXml2 (missing: LIBXML2_INCLUDE_DIR)
```

The existing Conan cache already contains the published `libxml2/2.15.3`
package, including:

```text
/storage/Users/currentUser/.conan2/p/libxma6fa3de616723/p/include/libxml2/libxml/xmlversion.h
/storage/Users/currentUser/.conan2/p/libxma6fa3de616723/p/lib/libxml2.so
```

Reconfiguring a separate Foundation XML probe with those explicit paths
succeeded without touching the stable Foundation build tree:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/configure-foundation-xml-probe2-20260802-212033.log
Found LibXml2: .../lib/libxml2.so (found version "2.15.3")
CONFIG_RC=0
```

That generated `_CFXMLInterface` and `FoundationXML` targets. A dry run showed
that building `FoundationXML` from this fresh build directory would trigger
574 steps, mostly rebuilding Foundation and ICU. The preferred next step is to
reuse the already validated `foundation-ohos-probe1` artifacts and only build
the new `_CFXMLInterface` plus seven `FoundationXML` Swift sources, instead of
starting a full Foundation rebuild.

Operational note: a memory check corrected the earlier `free -h` reading.
`free=2.6G` was bare free memory, while `/proc/meminfo` showed
`MemAvailable` around 14 GiB because most used memory was reclaimable page
cache. Later samples before the XML dry run stayed around 12.6 GiB
`MemAvailable` and about 49 GiB `SwapFree`. After the dry run, both FRP
`frp-tip.com:56267` and direct `10.62.230.12:2222` SSH began accepting the TCP
connection and immediately closing the session. No new Swift source failure was
observed in that disconnected window.

## 2026-08-02 FoundationXML and direct unxip binary success

The efficient FoundationXML path was validated without rebuilding the full
Foundation graph. The probe manually reused the previously validated Foundation
artifacts, built `_CFXMLInterface` plus the seven FoundationXML Swift sources,
linked `libFoundationXML.so`, and signed the result:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/foundationxml-irhandoff-20260802-214017.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/relink-foundationxml-probe2-20260802-214626.log
LINK_RC=0
SIGN_RC=0
```

`import FoundationXML` then typechecked when using the generated libdispatch
module map through the VFS overlay:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/verify-foundationxml-import-ninjadispatch-20260802-215708.log
TYPECHECK_RC=0
```

Two executable smokes also passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/verify-foundationxml-import-only-exe-20260802-220216.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/verify-foundationxml-xmldoc-exe-20260802-220452.log
COMPILE_RC=0
SIGN_RC=0
RUN_RC=0
stdout: toc
```

The `xz/5.6.2` Conan package in the device cache provides usable `lzma.h` and
`liblzma.a`:

```text
/storage/Users/currentUser/.conan2/p/xz22c09c364bc26/p/include/lzma.h
/storage/Users/currentUser/.conan2/p/xz22c09c364bc26/p/lib/liblzma.a
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-lzma-import-with-xz-cache-env-20260802-221415.log
TYPECHECK_RC=0
```

With Foundation, FoundationXML, libdispatch, libxml2, zlib, and xz include/lib
paths staged explicitly, the full direct `unxip` Swift source typecheck passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/typecheck-unxip-direct-parseaslib-20260802-222300.log
TYPECHECK_RC=0
```

The normal SwiftPM unxip build still has an orchestration boundary. A release
SwiftPM run with IR handoff and `j2` stopped making progress: `swift-build`
slept in `do_rt_sigsuspend`, no frontend children were visible, and the log did
not grow, so the probe was stopped and marked `BUILD_STOPPED_BY_CODEX`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/unxip-spm-release-irhandoff-j2-20260802-223538-b64.log
```

To avoid blocking on that SwiftPM process boundary, a direct Swift 6 optimized
unxip binary was built through the same proven IR handoff. This completed,
signed, and ran the CLI help smoke:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/unxip-direct-swiftc-irhandoff-concurrencyfix2-20260802-225605.log
[ohos-irhandoff] emit-ir rc=0 size=3656085
[ohos-irhandoff] opt rc=0
[ohos-irhandoff] clang rc=0 object-size=903152
BUILD_RC=0
SIGN_RC=0
HELP_RUN_RC=0
```

The produced executable is:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/unxip-direct-irhandoff-20260802-225607
```

Binary audit showed the OHOS musl interpreter, RUNPATH to the staged Swift,
Foundation, Dispatch, libxml2, and xz paths, and expected dynamic dependencies
on Swift runtimes, `libFoundationXML.so`, `libFoundation.so`,
`libswiftDispatch.so`, `libdispatch.so`, `libz.so`, `libxml2.so.16`, and
`libc.so`.

Temporary source fixes proven on the device and now represented in the recipe
preparation logic:

- Materialize the upstream `Sources/libunxip/libunxip.swift` symlink as a
  normal file on OHOS filesystems that reject link creation.
- Change system-library shim headers for `getopt`, `zlib`, and `lzma` to
  `#include_next` to avoid self-recursive imports after adding shim include
  directories to ClangImporter.
- Pass the package shim include directories plus dependency include paths to
  Swift via `-Xswiftc -Xcc -Xswiftc -I...`.
- Add `-parse-as-library`.
- Patch the two actor-local Swift 6 continuation calls to use
  `isolation: self`.
- In the Conan recipe, keep Linux `--static-swift-stdlib` behavior separate
  from OHOS. OHOS uses the SwiftPM OHOS triple, disables index-store, caps
  SwiftPM jobs, and relies on the staged Swift runtime/linker behavior proven
  by the toolchain probe.

Current boundary: the compiler/runtime path can build a real optimized unxip
binary on OHOS, but the reviewable package flow is not finished until SwiftPM
unxip no longer hangs in `swift-build` and the IR handoff, modulewrap, runtime
staging, signing, and SDK propagation behavior are formalized instead of
remaining probe wrappers.

## 2026-08-02 late SwiftPM unxip release success

The previous apparent SwiftPM hang was rechecked with a longer monitored
single-job run. It was not a permanent deadlock: SwiftPM spent several minutes
inside slow `swift-driver-new`/`swift-help`/manifest probes before continuing.
With the same staged Foundation, FoundationXML, libdispatch, libxml2, zlib, and
xz paths, a full SwiftPM release build for upstream `unxip` completed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/unxip-spm-release-irhandoff-longmon-j1-t1-20260802-234731.log
Build complete! (211.85s)
[ohos-irhandoff] emit-ir rc=133 size=5863471
[ohos-irhandoff] opt rc=0
[ohos-irhandoff] clang rc=0 object-size=699192
```

Produced artifacts:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/unxip-3.3-src/.build/aarch64-unknown-linux-ohos/release/unxip
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/unxip-3.3-src/.build/aarch64-unknown-linux-ohos/release/Modules/unxip.swiftmodule
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/unxip-3.3-src/.build/aarch64-unknown-linux-ohos/release/Modules/libunxip.swiftmodule
```

The resulting executable ran the CLI help smoke on the true device:

```text
HELP_RC=0
A fast Xcode unarchiver
USAGE: unxip [options] <input> [output]
```

Binary audit showed the OHOS musl interpreter, RUNPATH to the staged Swift
runtime, Foundation, FoundationXML, Dispatch, libxml2/xz package paths, and
expected dynamic dependencies on Swift runtimes, Foundation/FoundationXML,
Dispatch, `libz.so`, and `libc.so`.

The remaining reviewable boundary is no longer "SwiftPM cannot build unxip" but
"the successful SwiftPM path still depends on experimental toolchain behavior":
IR handoff for optimized object emission, modulewrap handling, runtime/library
staging, code signing, SDK/resource-dir propagation, symlink materialization,
and Swift 6 actor-isolation source fixes still need to be formalized before a
clean Conan package/CI result can be claimed.

## 2026-08-03 Conan create and test_package success

The Conan recipe was integrated with the same OHOS SwiftPM release path. A first
Conan run exposed one additional Swift 6 actor-isolation source boundary in
`PermissiveActionLink.next()`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/conan-create-unxip-swiftpm-irhandoff-20260803-0040.out
/storage/Users/currentUser/.conan2/p/b/unxipf1dece91696ff/b/unxip.swift:177:14:
error: sending 'self'-isolated value of type '(CheckedContinuation<Element?, any Error>) -> Void'
```

The recipe source preparation now patches both upstream entry points,
`unxip.swift` and the materialized `Sources/libunxip/libunxip.swift`, for this
four-tab continuation shape as well as the earlier continuation call sites.
After resyncing the recipe, the monitored true-device run built both optimized
Swift objects through the IR handoff:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/conan-create-unxip-swiftpm-irhandoff-20260803-004816.out
[ohos-irhandoff] emit-ir rc=133 size=7852463
[ohos-irhandoff] opt rc=0
[ohos-irhandoff] clang rc=0 object-size=916096
[ohos-irhandoff] emit-ir rc=133 size=5863283
[ohos-irhandoff] opt rc=0
[ohos-irhandoff] clang rc=0 object-size=699192
[6/7] Linking unxip
Build complete! (456.70s)
Package '15141ce3eb5a91ba7d0b3075840da216efff4f0c' created
```

The created package reference was:

```text
unxip/3.3@ohpcd/stable#f9fcc576fbe5befb3433e94facae4f04:15141ce3eb5a91ba7d0b3075840da216efff4f0c#e6fb8470213a704b353d7c0a80add145
/storage/Users/currentUser/.conan2/p/b/unxip07ec4440ee2f8/p/bin/unxip
sha256 a69bed8143713233b985478e77335dbace16751113c6d4b677282a6f83be505c
```

The first test_package attempt then failed only because the test recipe used a
fixed `/data/service/hnp/bin/bash` path that is absent on this true device:

```text
/system/bin/sh: /data/service/hnp/bin/bash: inaccessible or not found
ConanException: Error 127 while executing
```

`test_package/conanfile.py` now selects an available shell from `CONFIG_SHELL`,
`PATH`, common OHOS locations, or `/system/bin/sh`, and `test.sh` is POSIX-sh
compatible. Re-running the test package against the created package passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/conan-test-unxip-swiftpm-irhandoff-20260803-0104-test.out
unxip 3.3
TEST_RC=0
```

A final cached end-to-end `conan create` rerun, using the already built package
and the corrected test_package, also passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/conan-create-unxip-swiftpm-irhandoff-20260803-0105-full-create.out
unxip/3.3@ohpcd/stable (test package): Running test()
unxip 3.3
CREATE_RC=0
```

Package binary smokes:

```text
/storage/Users/currentUser/.conan2/p/b/unxip07ec4440ee2f8/p/bin/unxip --version
unxip 3.3
VERSION_RC=0

/storage/Users/currentUser/.conan2/p/b/unxip07ec4440ee2f8/p/bin/unxip --help
HELP_RC=0
A fast Xcode unarchiver
```

`llvm-objdump -p` on the packaged binary reports the OHOS musl loader string
`/lib/ld-musl-aarch64.so.1`, a RUNPATH to the staged Swift/Foundation/Dispatch
runtime plus Conan libxml2/xz package paths, and NEEDED entries for Swift
runtime libraries, Dispatch, Foundation/FoundationXML, and `libc.so`.

Current boundary after this run: unxip/3.3 has a true-device Conan create and
test_package pass under the experimental OHOS-native Swift 6.0.3 path. The
remaining work belongs to the Swift toolchain high-difficulty track: formalize
or publish the SwiftPM/SwiftDriver/frontend IR handoff, modulewrap, SDK/resource
propagation, runtime staging, and signing behavior so CI can reproduce this
without ad hoc probe wrappers and absolute staged runtime paths.
