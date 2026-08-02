# unxip 3.3 Path B Evidence

## Candidate Claim

`unxip` is blocked not by ordinary C/C++ dependencies, but by the absence of a
usable Swift 6 build toolchain on HarmonyOS PC. This round therefore records a
candidate Path B contribution: Swift toolchain availability and Linux binary
toolchain migration boundaries for OHOS/aarch64 packages.

Final scoring is subject to official review. This document does not claim that
Swift has been fully adapted yet; it records the reproducible evidence and the
next separable work item.

## Why This Is Beyond Basic Recipe Work

`unxip` 3.3 uses Swift Package Manager:

- `Package.swift` declares `swift-tools-version:6.0`.
- Upstream build entry is `swift build --configuration release`.
- Non-macOS builds import `FoundationXML`, `GNUSource`, `getopt`, `lzma`, and
  `zlib`.

The required C/C++ dependencies are already published in `ohpcd`:

- `libxml2/2.15.3`
- `xz/5.6.2`
- `zlib-ng-compat/2.3.3`

True-device CI reached `conan create` and failed only when the recipe checked for
Swift:

```text
ConanException: Swift 6 toolchain not found on PATH
```

## Official Swift Toolchain Probe

The official Swift 6.0.3 Ubuntu 22.04 aarch64 toolchain tarball exists and was
downloaded on the HarmonyOS device:

- URL: `https://download.swift.org/swift-6.0.3-release/ubuntu2204-aarch64/swift-6.0.3-RELEASE/swift-6.0.3-RELEASE-ubuntu22.04-aarch64.tar.gz`
- Size on device: `736M`
- SHA256 on device: `0ce755e7ed16fa07f6d1207a8135aff97e977653c1359011c60cb6d85a9cfa5b`
- Probe root: `/storage/Users/currentUser/swift-toolchain-probe`

The tarball lists a complete Swift toolchain layout, including:

```text
usr/bin/swift-driver
usr/bin/swift-frontend
usr/bin/swift-package
usr/bin/clang-17
usr/bin/lld
```

## Observed OHOS Migration Boundaries

### 1. Link extraction is restricted

Extracting the official tarball under the current OHOS user filesystem produced
link-creation failures:

```text
tar: can't link '.../usr/bin/swift' -> 'swift-driver': Permission denied
tar: can't link '.../usr/bin/swiftc' -> 'swift-driver': Permission denied
tar: had errors
```

The real target binaries were still partially extracted, so the next checks used
`swift-driver`, `swift-frontend`, and `swift-package` directly.

### 2. Unsigned Linux ELF binaries are denied

Before signing, direct execution of `swift-driver` returned:

```text
Permission denied
```

This matches the general OHOS requirement that foreign ELF binaries need
appropriate signing before execution can proceed far enough to expose runtime
loader errors.

### 3. After signing, Linux/glibc loader is missing

After signing `swift-driver` with the device signing tools from
`$HOME/usr/local/bin`, execution changed to:

```text
No such file or directory
```

`llvm-readobj` showed that the binary requests the Linux/glibc interpreter and
runtime libraries:

```text
interpreter: /lib/ld-linux-aarch64.so.1
NEEDED: libc.so.6
NEEDED: libm.so.6
NEEDED: libstdc++.so.6
NEEDED: libgcc_s.so.1
NEEDED: libncurses.so.6
NEEDED: libtinfo.so.6
NEEDED: libsqlite3.so.0
NEEDED: libswiftCore.so
NEEDED: libFoundation.so
RUNPATH: $ORIGIN/../lib/swift/linux
```

The device does not provide `/lib/ld-linux-aarch64.so.1`, and the official
Ubuntu toolchain tarball does not bundle that loader.

## Additional Official Source Check

Swift's Linux install page also provides an official Swiftly package for Linux
aarch64:

- URL: `https://download.swift.org/swiftly/linux/swiftly-aarch64.tar.gz`
- Size from HTTP HEAD: `27720097` bytes
- SHA256 from local download:
  `cc4f912fff6c7f53704fc6d22f9e8ee7fdf6bd574ad276998f7502418bf5a45a`

Local `readelf` inspection of the extracted `swiftly` binary showed:

```text
ELF64, AArch64, EXEC
no PT_INTERP program header
no dynamic section
```

This makes Swiftly a promising lightweight next probe because it should not hit
the exact `/lib/ld-linux-aarch64.so.1` loader failure before its own code starts
running. However, Swiftly is an installer/manager, not the Swift compiler
itself. The toolchains it installs are still expected to be the official Linux
Swift toolchains unless proven otherwise, so Swiftly does not by itself resolve
the Swift 6 host compiler boundary observed above.

## Swiftly True-Device Probe

Probe date: 2026-07-25.

Device state before the probe was already busy:

```text
load average: about 20
free memory: about 1.4G
```

The probe was therefore limited to Swiftly startup and initialization checks,
not a full Swift toolchain download/install.

Commands and observations:

```sh
cd /storage/Users/currentUser/swiftly-probe
wget -O swiftly-aarch64.tar.gz \
  https://download.swift.org/swiftly/linux/swiftly-aarch64.tar.gz
sha256sum swiftly-aarch64.tar.gz
tar -xzf swiftly-aarch64.tar.gz
```

Result:

```text
cc4f912fff6c7f53704fc6d22f9e8ee7fdf6bd574ad276998f7502418bf5a45a
```

Unsigned execution still hit OHOS executable policy:

```text
./swiftly: Permission denied
```

After signing with the device signing tool and preserving the executable name
as `swiftly`, the binary started:

```sh
$HOME/usr/local/bin/binary-sign-tool sign \
  -inFile swiftly \
  -outFile swiftly.signed \
  -selfSign 1
```

`swiftly --help` succeeded and showed the expected subcommands. Before
initialization, command execution reported the missing config file, which is
normal for Swiftly:

```text
Could not load swiftly's configuration file at
.../swiftly-home/config.json.
```

`swiftly init --skip-install` then exposed a new installer-level prerequisite:

```text
Error: The ca-certificates package is not installed.
```

The tested device has `/etc/ssl/certs`, but no common CA bundle files such as
`/etc/ssl/certs/ca-certificates.crt`,
`/etc/pki/tls/certs/ca-bundle.crt`, or `/etc/ssl/cert.pem`. The system
certificate directory is not writable by `currentUser`. Setting
`SSL_CERT_FILE=/storage/Users/currentUser/swiftly-probe/cacert.pem` did not
bypass Swiftly's preflight check.

As a proof-of-concept probe only, the Swiftly copy was patched so its hard-coded
`/etc/pki/tls/certs/ca-bundle.crt` check pointed to the same-length writable
path `/storage/Users/currentUser/a.pem`. After re-signing the patched copy and
running it as `swiftly`, initialization succeeded without downloading a Swift
toolchain:

```sh
./swiftly init \
  --platform ubuntu22.04 \
  --skip-install \
  --quiet-shell-followup \
  --assume-yes
```

Resulting config:

```json
{
  "version" : "1.1.3",
  "platform" : {
    "nameFull" : "ubuntu22.04",
    "namePretty" : "Ubuntu 22.04",
    "name" : "ubuntu2204"
  },
  "installedToolchains" : [

  ]
}
```

`swiftly --version` returned `1.1.3`, `swiftly list` succeeded with no installed
toolchains, and `swiftly list-available` succeeded, including these relevant
release toolchains:

```text
Swift 6.3.3
Swift 6.2.4
Swift 6.1.3
Swift 6.0.3
Swift 6.0.2
Swift 6.0.1
Swift 6.0.0
```

The next check should install a selected Swift 6 toolchain through the patched
Swiftly path and inspect the installed `swift` binary. That step was not started
because SSH began closing connections while the device was under high load.

After SSH recovered, a cautious install attempt was made with:

```sh
swiftly install 6.0.3 --no-verify --assume-yes --use
```

It stopped before installing a toolchain:

```text
Swiftly is currently unlinked and will not manage the active toolchain.
Error: The operation could not be completed. The file doesn’t exist.
Installing Swift 6.0.3
```

A later verbose diagnostic command timed out locally and left one `swiftly`
process on the device. At 18:37, that `swiftly` process (PID 48646) was
terminated. No installed Swift compiler was found, and the unrelated existing
`conan` process was not touched. The device load was still about 20, so the
full install and ELF verification should resume during an off-peak window.

2026-07-26 follow-up: the off-peak probe resumed. No Swift/Conan/clang/make
workload was visible, although `uptime` still reported load around 20 and `top`
showed the CPUs mostly idle. Swiftly successfully downloaded the complete
Swift 6.0.3 Ubuntu 22.04 aarch64 toolchain:

```text
100%: Downloaded 735.9 MiB of 735.9 MiB
```

Installation then failed while extracting the archive:

```text
Error: ExtractError(message: Optional("Can't create '/storage/Users/currentUser/swiftly-probe/isolated-home/.local/share/swiftly/toolchains/6.0.3/usr/bin/aarch64-swift-linux-musl-clang++.cfg'"))
```

That path is the first symlink-like config entry in the Swift toolchain archive
(`aarch64-swift-linux-musl-clang++.cfg -> aarch64-swift-linux-musl-clang.cfg`).
`swiftly list` still showed no installed release toolchains, and no installed
`swift` compiler binary was found beyond Swiftly proxy executables. The next
toolchain task should therefore handle archive link extraction/layout on OHOS
before continuing to signed ELF interpreter and runtime checks.

## Link-Flatten And ELF Runtime Probe

The 2026-07-26 04:00 heartbeat found no Apache/Arrow/Conan/clang/make/ninja or
Swiftly workload. Although `uptime` still reported load around 20, `top` showed
the CPUs mostly idle, so a non-CI Swift toolchain probe resumed.

The existing verified Swift 6.0.3 tarball was reused; no re-download was needed:

```text
/storage/Users/currentUser/swift-toolchain-probe/swift-6.0.3-RELEASE-ubuntu22.04-aarch64.tar.gz
SHA256: 0ce755e7ed16fa07f6d1207a8135aff97e977653c1359011c60cb6d85a9cfa5b
```

The previous partial extraction already contained the real binaries and runtime
libraries. The probe flattened the minimum link-style entries needed to continue
ELF verification:

```text
swift -> swift-driver
swiftc -> swift-driver
clang -> clang-17
aarch64-swift-linux-musl-clang++.cfg -> aarch64-swift-linux-musl-clang.cfg
```

After that, `swift`, `swiftc`, `swift-driver`, `swift-frontend`,
`swift-package`, `clang`, and `clang-17` were all ordinary files in the extracted
`usr/bin`.

`llvm-readobj` and `strings` on the flattened `swift` binary showed:

```text
PT_INTERP
/lib/ld-linux-aarch64.so.1
NEEDED: libswiftCore.so
NEEDED: libFoundation.so
NEEDED: libm.so.6
NEEDED: libstdc++.so.6
NEEDED: libgcc_s.so.1
NEEDED: libc.so.6
RUNPATH: $ORIGIN/../lib/swift/linux
```

`swift-frontend` also has a `PT_INTERP` program header and Linux/glibc runtime
dependencies.

Runtime results:

```text
unsigned swift --version: No such file or directory
signed swift --version:   No such file or directory
signed swift-frontend:    No such file or directory
```

The signed binaries were produced with:

```sh
$HOME/usr/local/bin/binary-sign-tool sign -inFile swift -outFile swift.signed -selfSign 1
```

Conclusion: link-flattening resolves the archive layout boundary enough to
inspect and attempt the compiler binaries, but the official Ubuntu Swift 6.0.3
compiler still cannot execute on OHOS because it requests the Linux/glibc
loader `/lib/ld-linux-aarch64.so.1`. This keeps `unxip` blocked on a separate
Swift host toolchain/runtime strategy.

## Glibc Runtime Bundle Probe

To distinguish “missing loader” from a broader Linux/glibc execution boundary,
a minimal Ubuntu 22.04 arm64 runtime bundle was assembled from official
`ports.ubuntu.com` packages:

```text
libc6_2.35-0ubuntu3.13_arm64.deb
libgcc-s1_12.3.0-1ubuntu1~22.04.3_arm64.deb
libstdc++6_12.3.0-1ubuntu1~22.04.3_arm64.deb
libncurses6_6.3-2ubuntu0.2_arm64.deb
libtinfo6_6.3-2ubuntu0.2_arm64.deb
libsqlite3-0_3.37.2-2ubuntu0.7_arm64.deb
zlib1g_1.2.11.dfsg-2ubuntu9.2_arm64.deb
libuuid1_2.37.2-4ubuntu3.5_arm64.deb
```

The bundle materialized Debian symlinks as regular files and includes:

```text
ld-linux-aarch64.so.1
libc.so.6
libm.so.6
libstdc++.so.6
libgcc_s.so.1
libncurses.so.6
libtinfo.so.6
libsqlite3.so.0
libz.so.1
libuuid.so.1
```

The uploaded bundle path was:

```text
/storage/Users/currentUser/swift-toolchain-probe/glibc-runtime-ubuntu2204-arm64/
```

After signing `ld-linux-aarch64.so.1`, the loader itself runs:

```text
loader_signed_exit=0
Usage: .../ld-linux-aarch64.so.1.signed [OPTION]... EXECUTABLE-FILE ...
```

Running signed or unsigned Swift through the signed loader still fails:

```text
swift_loader_exit=127
.../swift.signed: error while loading shared libraries:
.../swift.signed: failed to map segment from shared object

frontend_loader_exit=127
.../swift-frontend.signed: error while loading shared libraries:
.../swift-frontend.signed: failed to map segment from shared object
```

To check whether this was Swift-specific, a small Ubuntu `coreutils` `true`
binary was extracted and tested through the same signed loader and library path.
It failed the same way:

```text
true_orig_exit=127
.../true.arm64: error while loading shared libraries:
.../true.arm64: failed to map segment from shared object

true_signed_exit=127
.../true.signed: error while loading shared libraries:
.../true.signed: failed to map segment from shared object
```

This establishes a broader boundary: a signed Ubuntu glibc loader can start on
OHOS, but loader-mediated mapping of Linux/glibc executable segments fails even
for a minimal program. The official Linux Swift toolchain therefore cannot be
made usable by merely bundling glibc runtime libraries in user space.

A follow-up mount/execution check showed `/storage/Users/currentUser` is mounted
without an explicit `noexec` flag, and both the signed Swiftly binary and signed
`ld-linux-aarch64.so.1` can start from the probe paths. Direct execution of the
signed Ubuntu `true` binary still reports `No such file or directory` because
its PT_INTERP points to the Linux loader path. Running it through the signed
loader reaches the deeper `failed to map segment from shared object` boundary.
This makes a simple noexec-directory explanation unlikely.

## Current Conclusion

Official Swift Linux/aarch64 binaries are a real upstream source, but they are
not directly usable as an OHOS native Swift 6 toolchain. The immediate missing
piece is not `unxip` source adaptation; it is a reusable Swift toolchain
strategy for OHOS:

1. provide an OHOS-native Swift 6 toolchain, or
2. establish an approved platform-level Linux/glibc compatibility boundary
   that can map and run Linux/glibc executables, or
3. use Swift's static Linux SDK only if it can be driven by an executable Swift
   host toolchain on OHOS.

## External Source And Target Check

Follow-up source review on 2026-07-26 did not identify a ready OHOS Swift host
toolchain in the local archive set or `cmd-pkgs`. The only Swift-related
published recipe found locally is `libdispatch/5.10.1`, and that recipe builds
with Swift disabled (`ENABLE_SWIFT=OFF`), so it does not provide a Swift
compiler path.

Swift.org's official install material confirms there are Linux/aarch64 Swift
toolchains, Swiftly, and a Static Linux SDK workflow. These are still not a
complete answer for this device:

- newer official Linux/aarch64 releases remain Linux toolchains, so they should
  be expected to hit the same glibc loader/runtime class until proven otherwise;
- Swiftly is an installer/manager and has already been proven executable after
  signing, but the compiler it installs is still the official Linux Swift
  toolchain;
- Static Linux SDK is driven through `swift sdk install` and `swift build`, so
  it still needs a working host `swift` first;
- Swift's own source build instructions require a prebuilt Swift toolchain on
  the host to build Swift components, so an OHOS-native Swift host build needs
  a bootstrap plan rather than only the existing OHOS C/C++ toolchain.

A lightweight true-device string scan of the extracted official Swift 6.0.3
Ubuntu 22.04 aarch64 package also found no `ohos`, `OpenHarmony`, or
`aarch64.*linux.*ohos` target markers in common text/config files or in
`swift-driver`, `swift-frontend`, and `clang-17`. This is not a formal upstream
support proof, but it supports the current engineering direction: stop treating
the official Linux tarball as a near-fix and move the work to either an
OHOS-native Swift host toolchain or an approved platform-level Linux/glibc
execution layer.

## Mainline OHOS-Native Direction

The mainline exploration is recorded in
`archives/u/unxip/3.3/reports/swift-mainline-ohos.md`.

True-device smoke checks show the OHOS-native C/C++ substrate is usable once the
environment is set correctly:

- `$HOME/usr/local/bin/clang-15` runs directly and reports target
  `aarch64-unknown-linux-ohos`;
- `$HOME/usr/local/bin/clang` and `clang++` are shell wrappers, so direct
  execution can return `Permission denied`; invoking them through `sh ./clang`
  and `sh ./clang++` works;
- `TMPDIR` must point to a writable user directory, otherwise clang fails with
  `unable to make temporary file: Read-only file system`;
- after setting `TMPDIR`, a C smoke binary built and ran with exit 0, and a C++
  smoke binary built and printed `42`;
- `llvm-readobj` confirms the outputs are OHOS/AArch64 ELF executables needing
  `libc.so` and, for C++, `libc++_shared.so`.

This is a positive substrate check, but not a Swift solution by itself. The
missing mainline work remains Swift-specific: add/verify OHOS triple/platform
handling in Swift/SwiftPM, build Swift runtime/stdlib for OHOS, cross-build an
OHOS-host Swift toolchain from a Linux bootstrap host, sign the resulting host
tools, and only then verify `swift --version` on the device.

## Path B Framing

Application issue:
`https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1438`.

Candidate Path B value:

- identifies a non-obvious build-language/toolchain blocker for Swift packages
  on OHOS;
- separates published C/C++ dependency readiness from Swift toolchain readiness;
- records reproducible evidence for official Swift Linux/aarch64 binaries:
  download source, checksum, extraction failure mode, signing transition, ELF
  interpreter, NEEDED libraries, and final runtime failure;
- creates a reusable knowledge draft for future SwiftPM packages rather than
  treating `unxip` as an isolated failure.

## Next Work Item

Continue the separate Swift toolchain exploration before retrying `unxip`.
The official Ubuntu Swift route has now reached a reproducible boundary:
link-flattening helps archive layout, and a signed glibc loader can start, but
loader-mediated execution still fails even for Ubuntu `true`.

The next useful work is therefore not another `unxip` CI run. It is to find or
build a true OHOS-capable Swift 6 host toolchain, or to prove a platform-owned
Linux/glibc compatibility mechanism that can run a minimal Linux/glibc
executable before attempting Swift again.

## 2026-07-28 Source-Build Progress

The mainline path has shifted from the official Linux/glibc tarball probe to an
OHOS-native Swift source-build probe. On the true device, the Swift 6.0.3 source
tree and OHOS LLVM15 fork are being built under
`/storage/Users/currentUser/swift-mainline-ohos-src` with
`TMPDIR=/storage/Users/currentUser/swift-mainline-ohos-src/tmp`.

Evidence collected so far:

- IRGen progressed beyond previous LLVM15 API mismatches, including the
  `MetadataRequest.cpp` `setMemoryEffects` incompatibility.
- Swift TextAPI/TBD generation now compiles after mapping newer
  `EncodeKind`/`TBD_V5`/`SymbolFlags::Text|Data` usage onto LLVM15 TextAPI.
- The build then reached frontend CAS/diagnostics code; missing CAS schema,
  CAS file-system, tree-builder, `ObjectProxy::getMemoryBuffer`,
  `PrefixMapper`, VFS, and compression compatibility gaps were shimmed to keep
  CAS disabled-but-compilable on OHOS LLVM15.
- The 2026-07-28 22:43 CST rebuild validated the next CAS shim layer:
  `createUnknownObjectError(const CASID &)`, `ObjectProxy::getData()` as
  `StringRef`, an `AsyncProxyValue::take()` wrapper, and `raw_ostream`
  printing for `CASID`.
- With those shims synced to the device, the build passed the previous
  `CachingUtils.cpp`/`CompileJobCacheResult.cpp` boundary, rebuilt through
  `libswiftAST.a` and `libswiftSIL.a`, and reached `[270/807]` in
  `lib/Sema`.
- The run was manually paused with `BUILD_EXIT=2` when another true-device
  `vapoursynth` Conan heavy task started. No new Swift compile/link failure was
  observed before the pause. Latest log:
  `/storage/Users/currentUser/swift-mainline-ohos-src/logs/swift-build-frontend-20260728-224302.log`.
- A later 23:00 CST resume reused the same build graph (`[1/537]`), linked
  `libswiftSema.a`, entered `SILGen` and `SILOptimizer`, and reached
  `[139/537]` (approximately `[409/807]` in the original graph) at
  `lib/SILOptimizer/Differentiation/Common.cpp.o`.
- That later run was again manually paused with `BUILD_EXIT=2` when the
  `vapoursynth` Conan heavy task restarted at 23:06 CST. No new Swift
  compile/link failure was observed. Latest log:
  `/storage/Users/currentUser/swift-mainline-ohos-src/logs/swift-build-frontend-20260728-230059.log`.
- A later 23:55 CST resume started from `[1/398]`, advanced through more of
  `SILOptimizer`, entered `IRGen`, and reached `[218/398]` at
  `lib/IRGen/GenClangType.cpp.o`. It was paused at 00:05 CST when a separate
  `xapian-core` Conan heavy task started on the true device. No new Swift
  compile/link failure was observed. Latest log:
  `/storage/Users/currentUser/swift-mainline-ohos-src/logs/swift-build-frontend-20260728-235546.log`.
- A 00:08 CST resume validated the `CompilerInvocation.cpp` compatibility
  fixes, then exposed a Clang serialized-diagnostics schema gap:
  `RECORD_SOURCE_FILE_CONTENTS` is present in Swift 6's serializer but absent
  from the OHOS LLVM15 Clang header. The compatibility header was extended, and
  the next run compiled `SerializedDiagnosticConsumer.cpp` and linked
  `libswiftIRGen.a`.
- The latest boundary is no longer C++ API compatibility but OHOS filesystem
  behavior: the build directory has `SWIFT_USE_SYMLINKS=ON`, causing
  `cmake -E create_symlink` for migrator JSON data to fail with
  `Permission denied`. The intended next step is to reconfigure this build dir
  with `SWIFT_USE_SYMLINKS=OFF` and continue from the same incremental graph.
- A 2026-07-29 CST follow-up moved past that build-system boundary. The
  OHOS-native `swift`, `swiftc`, and `swift-frontend` binaries were produced
  and `swift --version` now reports Swift 6.0.3 with target
  `aarch64-unknown-linux-ohos`.
- The current blocker is first-time Clang module/PCM creation for
  `SwiftShims`. Clean-cache `import SwiftShims` crashes with `RC=133` after
  `CreateWrappedASTConsumer` returns a non-null consumer. If a crashed run
  leaves `SwiftShims.pcm` behind, a cache-reuse probe can pass, which narrows
  the failure to PCM creation/finalization rather than host executable startup.
- The 2026-07-29 diagnostic rebuild validated additional LLVM15 compatibility
  work: `Compression.h` zlib/zstd `decompress(...)` aliases,
  `CodeGenRegisters.h` SetVector declaration cleanup, rebuilt
  `libLLVMipo.a`/`libLLVMLTO.a`, and a relinked `swift-frontend`. A finer
  `FrontendAction.cpp` marker patch has been synced to the true device and is
  waiting for the next free-device rebuild window.
- A later 2026-07-29 16:00 CST probe narrowed the clean-cache crash into
  `ObjectFilePCHContainerGenerator` during
  `clang::EmitBackendOutput(... Backend_EmitObj ...)`, after
  `PCHGenerator::Writer.WriteAST` had completed. A minimal Swift-side
  ClangImporter experiment has been synced to the true-device Swift source to
  route OHOS targets through raw PCM containers instead of object PCH
  containers. The experiment has not been rebuilt yet because
  `apache-arrow-glib` was running a true-device `make -j20` build at 16:13 CST.
- After the device cleared, that ClangImporter raw PCM experiment was rebuilt
  and validated. `swift-frontend` rebuilt with `RC=0`, a clean-cache
  `import SwiftShims` probe completed with `RC=0`, and
  `swiftCore-swiftmodule-ohos-aarch64` completed with `RC=0`. The latter
  produced `Swift.swiftmodule/aarch64-unknown-linux-ohos.swiftmodule` and
  `.swiftdoc`.
- A 2026-07-30 CST follow-up advanced the next target,
  `swiftCore-ohos-aarch64`, from `Swift.o` generation to a completed
  `libswiftCore.so`. The direct Swift embedded backend crashed in LLVM's
  `AArch64 Assembly Printer`; an OHOS-specific IR handoff experiment emitted
  `Swift.ll` and compiled it through the OHOS LLVM fork's `clang-15` into a
  valid aarch64 relocatable object. Once that bypass was installed as a narrow
  build-tree `swiftc` wrapper for stdlib `Swift.o`, the build reached the
  runtime link and exposed missing PIC on runtime/support object targets. A
  generated `build.ninja` experiment added `-fPIC` to 95 OHOS/aarch64
  runtime/support compile edges, after which
  `build-swiftCore-ohos-aarch64-pic-runtime-20260730-115544.log` completed with
  `RC=0` and produced
  `lib/swift/ohos/aarch64/libswiftCore.so` as a 34 MiB aarch64 ELF shared
  object.
- The next stdlib target boundary is the OHOS Platform/Glibc overlay. The
  top-level `stdlib/swift-stdlib-ohos-aarch64` graph referenced
  `swiftGlibc-swiftmodule-ohos-aarch64`, but
  `stdlib/public/Platform/CMakeLists.txt` did not generate Glibc overlay or
  `glibc.modulemap` targets for OHOS. A source experiment added OHOS to the
  Glibc overlay target set and to the modulemap generation loop, while keeping
  OHOS out of the `link "dl"` modulemap rule because OHOS has no separate
  `libdl`.
- That experiment generated `lib/swift/ohos/aarch64/glibc.modulemap` and
  `SwiftGlibc.h`, then exposed two host-environment requirements:
  `TMPDIR` must be writable for Swift driver supplementary outputs, and
  `SWIFT_SDK_OHOS_ARCH_aarch64_PATH` must point at
  `/storage/Users/currentUser/usr/local/sysroot` instead of `/` so ClangImporter
  can see OHOS sysroot headers such as `sys/ioctl.h`. `LibcOverlayShims.h` also
  needs to guard semaphore wrappers with `__has_include(<semaphore.h>)`, because
  the tested OHOS sysroot does not provide `semaphore.h`.
- With `TMPDIR` and the real sysroot path applied, the rerun
  `/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swiftGlibc-ohos-aarch64-sysroot-20260730-122806.log`
  advanced to at least `[471/916]` with no compile failure recorded. The device
  then entered sustained memory pressure (`Out of memory`, `can't fork` on SSH
  checks). This is currently a resource boundary, not a confirmed Swift source
  failure; final run state must be rechecked once SSH is stable.
- A 2026-07-30 14:56 CST reconnection window found the original Swift build
  host pingable but unavailable over both `10.62.230.12:2222` and
  `frp-tip.com:56267`. The separate `frp-tip.com:33332` O machine was reachable
  but did not have the `swift-mainline-ohos-src` tree, so it was not used for
  this lane. The next actionable step remains a state check on the original
  build tree once user-space sshd or the old-O tunnel is restored.

This strengthens the Path B/C evidence because the blocker is now demonstrably
inside Swift host toolchain adaptation across Swift, LLVM TextAPI, LLVM CAS,
VFS, compression, Clang module generation, LLVM backend object emission,
runtime PIC/linking, OHOS Platform/Glibc overlay generation, sysroot selection,
and OHOS signing/runtime constraints. It is not a normal Conan package recipe
problem.

## 2026-07-30 Evening Evidence Update

The SwiftGlibc overlay has now passed the concrete module lookup boundary. An
explicit `-Xcc -fmodule-map-file=.../lib/swift/ohos/aarch64/glibc.modulemap`
probe proved that `SwiftGlibc` was not inherently unavailable after target
generation; the remaining failures were generated-modulemap and OHOS libc
compatibility issues. The remote build-tree experiment fixed those by resolving
`assert.h` through the staged OHOS sysroot, removing the unavailable `CUUID`
modulemap block, and mapping OHOS `sighandler_t` without depending on glibc's
private `__sighandler_t`.

Verification:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swiftGlibc-swiftmodule-ohos-aarch64-flags-20260730-184945.log
RC=0
```

The full `stdlib/swift-stdlib-ohos-aarch64` chain is running next, not yet
claimed complete. During this resume, `Swift.o` and `SwiftOnoneSupport.o`
required the same OHOS IR-to-clang object handoff pattern, and a subsequent
`libswiftCore.so` link attempt exposed non-PIC OHOS/aarch64 runtime objects.
The current generated-build experiment adds `-fPIC` to OHOS/aarch64 C/C++ flags
and reruns the broad stdlib graph with `nice -n 10 ninja -j1`.

Current monitored run:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-stdlib-ohos-aarch64-full-j1-20260730-191240.log
2026-07-30 19:25 CST: [132/1086], no FAILED/error/segfault marker, about 14 GiB MemAvailable
```

This evidence increases the difficulty framing: the work crosses generated
Swift overlay targets, ClangImporter modulemap plumbing, OHOS sysroot/header
differences, Swift backend object emission, and shared-runtime PIC/linking. It
still remains a candidate claim only; the full stdlib/runtime chain must finish
and produce verifiable artifacts before it can be presented as completed.

## 2026-07-30 Late Evening Stdlib Evidence

The next stdlib resume moved beyond SwiftGlibc and confirmed a repeatable
OHOS-specific pattern in private stdlib libraries: Swift frontend can often
produce SIL and non-empty LLVM IR for the OHOS target, but the direct object
emission path traps. Stripping debug metadata from the emitted IR and compiling
that IR through the OHOS LLVM fork's clang wrapper produced valid aarch64
relocatable objects.

Validated object handoffs in this window:

- `SwiftPrivate.o`: `SwiftPrivate.correct.ll` (about 700 KiB) verified with
  `opt -verify`; `SwiftPrivate.strip-clang.o` (about 123 KiB) built with the
  OHOS clang wrapper and was copied by a single patched Ninja edge.
- `SwiftPrivateLibcExtras.o`: `SwiftPrivateLibcExtras.correct.ll` (about
  530 KiB) verified and compiled into `SwiftPrivateLibcExtras.strip-clang.o`
  (about 92 KiB), then attached with a single patched Ninja edge.
- `SwiftPrivateThreadExtras.o`: after an OHOS pthread model fix, the type
  errors moved to the same backend/object-emission trap. The watchdog-wrapped
  IR probe produced `SwiftPrivateThreadExtras.correct.ll` (about 359 KiB) and
  an object-ready `SwiftPrivateThreadExtras.strip-clang.o`. After SSH
  recovered, the follow-up copy-rule patch was confirmed and executed; the
  target is now a 64 KiB arm64 ELF relocatable.

The `SwiftPrivateThreadExtras.swift` source experiment is another source-level
OHOS compatibility item: OHOS imports `pthread_t` as an opaque pointer type and
`pthread_create` expects a pointer to optional `pthread_t`, so the ordinary
glibc/Linux `_make_pthread_t() -> pthread_t { pthread_t() }` path is not valid.
The remote source now excludes `SWIFT_STDLIB_OS_OHOS` from that Linux branch,
and generated OHOS Swift compile commands were patched to pass
`-D SWIFT_STDLIB_OS_OHOS` consistently.

Representative logs:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-SwiftPrivate-ll-opt-clang-20260730-221949.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-SwiftPrivateLibcExtras-ll-opt-clang-20260730-222354.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-SwiftPrivateThreadExtras-20260730-223719.status
/storage/Users/currentUser/swift-mainline-ohos-src/logs/watch-probe-SwiftPrivateThreadExtras-20260730-223719.log
```

The boundary before the final resume was the next unobserved stdlib graph node,
not the `SwiftPrivateThreadExtras` object. Direct SSH to `10.62.230.12:2222`
reset during key exchange immediately after the object probe, but later
recovered and the copy edge was installed. No package CI was started in that
window.

## 2026-07-30 Final Stdlib Evidence

The constrained final resume completed the full OHOS stdlib/runtime graph:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-stdlib-ohos-aarch64-full-j1-20260730-230325.log
END=2026-07-30 23:04:01 CST rc=0
```

Additional true-device checks:

- `build.ninja` contains the explicit SwiftGlibc modulemap flag:
  `-fmodule-map-file=/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos/aarch64/glibc.modulemap`.
- A minimal `import Glibc` typecheck with that modulemap, the staged OHOS
  sysroot, and the built resource dir returned `typecheck_rc=0`.
- `swift --version` and `swiftc --version` both report Swift 6.0.3 with target
  `aarch64-unknown-linux-ohos`.
- `nice -n 10 ninja -n stdlib/swift-stdlib-ohos-aarch64` returned
  `ninja_dry_rc=0`; it listed only five host helper/share regeneration actions,
  not new OHOS stdlib/runtime library edges.

Produced OHOS/aarch64 artifacts include `libswiftCore.so`, `libswiftGlibc.so`,
`libswiftSwiftOnoneSupport.so`, `libswiftSwiftPrivate.so`,
`libswiftSwiftPrivateLibcExtras.so`, `libswiftSwiftPrivateThreadExtras.so`,
`libswift_Builtin_float.so`, `libswiftRuntimeUnittest.so`,
`libswiftStdlibUnittest.so`, `libswiftStdlibUnicodeUnittest.so`,
`libswiftStdlibCollectionUnittest.so`, `libswiftRemoteMirror.so`, and
`bin/swift-reflection-test-OHOS`.

Installed OHOS target modules now include `Swift`, `Glibc`,
`SwiftOnoneSupport`, `SwiftPrivate`, `SwiftPrivateLibcExtras`,
`SwiftPrivateThreadExtras`, `_Builtin_float`, `RuntimeUnittest`,
`StdlibUnittest`, `StdlibUnicodeUnittest`, and `StdlibCollectionUnittest` as
`aarch64-unknown-linux-ohos.swiftmodule`.

Dynamic dependency spot checks show the produced stdlib libraries depend on
OHOS/system-shaped libraries rather than Linux/glibc sonames:

```text
libswiftCore.so:  libc++_shared.so, libc.so
libswiftGlibc.so: libswiftSwiftOnoneSupport.so, libswiftCore.so,
                  libc++_shared.so, libc.so
```

This is a major Path B/C evidence milestone, but still not a final reusable
toolchain claim. The successful state depends on remote build-tree experiments
that must be promoted into clean source-level patches and then retested before
`unxip` SwiftPM CI can be rerun.

## 2026-07-30 User Program Runtime Evidence

Two user-program smoke checks now prove that the produced OHOS Swift runtime can
execute signed Swift binaries when object emission is bridged through verified
LLVM IR and the OHOS clang wrapper:

- `probe-hello-ir-continue-20260730-233205.log`: minimal `print` program,
  `opt -verify`, `opt -S -strip-debug`, OHOS clang object compilation, link,
  sign, and run all returned rc 0; output was `hello-ohos-swift`.
- `probe-hello-glibc-ir-run-20260730-234506.log`: minimal `import Glibc`
  program produced usable IR despite frontend signal 5 (`emit_ir_rc=133`);
  autolink extracted `-lswiftSwiftOnoneSupport`, `-lswiftCore`, and
  `-lswiftGlibc`; link/sign/run returned rc 0 with output
  `hello-ohos-glibc`.

This is stronger than a library-only build proof because it exercises the
staged Swift modules, autolink extraction, OHOS stdlib shared libraries,
runtime `LD_LIBRARY_PATH`, code signing, and actual process launch. The
remaining compiler boundary is still significant: ordinary `swiftc` user
compile and even `swiftc -frontend -emit-ir` exit with signal 5 after writing
IR, so the current path is not yet a reusable toolchain claim.

Additional current limits:

- `swift package --version` fails because `swift-package` is absent.
- `swift build --help` fails because `swift-build` is absent.
- LLDB cannot currently capture a backtrace because `liblldb.so` relocates
  against Python 3.11 symbols that are unavailable in the tested environment.

## 2026-07-31 Frontend Object Emission Evidence

The signal 5 boundary has been narrowed to LLVM `TargetMachine` destruction on
the OHOS-hosted Swift frontend. Instrumented true-device runs showed the
frontend completed IRGen, `IRGenModule::finalize`, `embedBitcode`,
`IRGenModule::intoGeneratedModule`, `performLLVM`, and `generateCode`. The trap
occurred when `GeneratedModule` destroyed its owned `TargetMachine`.

An experimental OHOS-host workaround that releases the `GeneratedModule`
`TargetMachine` before destroying the LLVM module/context changed the minimal
frontend result from rc 133 to rc 0:

- `probe-gm-target-release-20260731-004308.log`: minimal `emit-irgen` returned
  rc 0 and reached `after performAction hadError=0`.
- `probe-after-target-release-20260731-004347-emit-ir.log`: minimal `emit-ir`
  returned rc 0.
- `probe-after-target-release-20260731-004347-c.log`: minimal
  `swiftc -frontend -c` returned rc 0 and produced an arm64 ELF relocatable
  object.
- `probe-driver-after-target-release-20260731-004430-glibc-emit-ir.log`:
  `import Glibc` `emit-ir` returned rc 0 with the OHOS `glibc.modulemap`.

This is a major improvement over the previous manual IR handoff: direct
frontend IR and object emission can now return successfully in the experimental
build tree. The remaining package-blocking boundary is the complete driver and
SwiftPM layer. The legacy driver still lacks `swift-driver-new`, requires a
writable `TMPDIR`, and dry-runs a link through
`/storage/Users/currentUser/usr/local/bin/clang -fuse-ld=gold` rather than the
manually successful OHOS clang wrapper/lld path.

## 2026-07-31 Legacy Driver Link Breakthrough

The frontend `TargetMachine` workaround was rebuilt in a cleaner form after
removing the `FrontendTool.cpp` probe prints:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swift-frontend-clean-targetmachine-release-20260731-005549.log
[17/17] Linking CXX executable bin/swift-frontend
rc=0
```

Minimal frontend checks now return rc 0 for all three important paths:

- `swiftc -frontend -emit-ir`
- `swiftc -frontend -c`
- `swiftc -frontend -emit-ir` with `import Glibc` and the generated OHOS
  `glibc.modulemap`

Evidence:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-clean-frontend-20260731-010143-emit-ir.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-clean-frontend-20260731-010143-c.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-clean-frontend-20260731-010143-glibc-emit-ir.log
RC emit_ir=0 frontend_c=0 glibc_emit_ir=0
```

The complete `swiftc` driver failure was then split into its generated stages.
The frontend compile and `swift-autolink-extract` stages both returned rc 0;
only the final clang link stage failed because Swift's legacy driver directly
execed a shell clang wrapper on HMDFS:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-driver-segments-20260731-010632.frontend.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-driver-segments-20260731-010632.autolink.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-driver-segments-20260731-010632.link.log
RC frontend=0 autolink=0 link=126
sh: .../usr/local/bin/clang: Permission denied
```

Direct `clang-15` ELF linking proved the link inputs were sound and that OHOS
needs `-Wl,--code-sign` for runnable user programs. A small OHOS-specific
driver experiment now makes the legacy driver:

- default to `lld` for `llvm::Triple::isOHOSFamily()`;
- pass `-Wl,--code-sign` on OHOS dynamic link jobs;
- choose executable `clang-15` instead of the shell `clang` wrapper.

Rebuild and direct driver verification:

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

This changes the evidence level again: the experimental OHOS-hosted Swift 6.0.3
tree can now run a direct `swiftc` driver compile/link/sign/run smoke. It is
not yet a packaged Swift toolchain because `swift-driver-new`, `swift-package`,
and `swift-build` remain absent, and several older source probes must still be
removed or formalized before a clean patch series can be proposed.

## 2026-07-31 Swift Driver Dependency Chain Probe

The next stage moved toward the missing `swift-driver-new` layer. The true
device has `repos/swift-driver` and `repos/swiftpm`, but the current compiler
build graph has no `swift-driver`, `swift-package`, or `swift-build` targets.

A separate `swift-driver` CMake probe configured with the experimental OHOS
`swiftc`, then failed at the first unstaged dependency:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swift-driver-ohos-probe2-20260731-012633.log
error: no such module 'TSCBasic'
RC=1
```

Because the true device lacks `git`/`curl`, the pinned dependency revisions were
fetched on the Windows host and transferred into the true-device CMake `_deps`
area:

```text
swift-argument-parser: 8f4d2753f0e4778c76d5f05ad16c74f707390531
swift-llbuild: a3b8d34be319f1b3ba8de53c434386419dec1f4f
swift-tools-support-core: 3b13e439a341bbbfe0f710c7d1be37221745ef1a
Yams: 0d9ee7ea8c4ebd4a489ad7a73d5c6cad55d6fed3
swift-system: 025bcb1165deab2e20d4eaba79967ce73013f496
```

That advanced the driver dependency chain through several additional platform
requirements:

- CMake/llbuild must use real `clang-15` for CXX, not the HMDFS shell
  `clang++` wrapper. `CMAKE_CXX_COMPILER_ARG1=--driver-mode=g++` gets CXX
  configure past this boundary.
- `llbuild` requires SQLite3. A temporary staging build of sqlite3 3.49.1 now
  exists at `/storage/Users/currentUser/swift-mainline-ohos-src/stage/sqlite3-3.49.1-ohos`.
- TSC requires a separately built `SwiftSystemConfig.cmake`, so SwiftSystem
  must be built before the driver/TSC layer.
- SwiftSystem needs an OHOS `O_ACCMODE` shim because OHOS `fcntl.h` defines
  `O_ACCMODE` through `O_SEARCH`, which ClangImporter cannot import. The
  experiment uses `03 | O_PATH`, and `O_PATH` was verified importable.

SwiftSystem then reached a compiler backend boundary. Direct object emission for
`SystemPackage` crashes with signal 11 even with whole-module mode and one Swift
thread:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-install-swift-system-ohos-wmo-20260731-015452.log
swiftc -frontend -c -primary-file .../Sources/System/Errno.swift ...
Signal 11
```

The same frontend command changed to `-emit-ir` succeeds and produces IR:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-swiftsystem-errno-emit-ir-20260731-015452.log
RC=0
OUT_SIZE=292096
```

This means the `swift-driver-new` route has progressed beyond missing source
dependencies and into the next object-emission/IR-handoff boundary. The likely
next experiment is to apply the same IR-to-OHOS-clang handoff pattern to
SwiftSystem, then resume SwiftSystem -> TSC -> LLBuild -> SwiftDriver.

Further exploration should evaluate:

- whether a true OHOS Swift target/toolchain exists upstream or in community
  channels;
- whether Swift can be built or bootstrapped as an OHOS host toolchain using
  the existing OHOS native C/C++ toolchain and signed host executables;
- whether the `failed to map segment from shared object` boundary is caused by
  executable policy, filesystem mount behavior, ELF segment layout, or an
  unsupported Linux/glibc loader model;
- whether any platform-approved Linux compatibility layer can run a minimal
  Ubuntu/glibc executable before Swift is retried;
- whether Swift static Linux SDK helps only after the host `swift` executable
  itself can run on OHOS.

## 2026-07-31 FoundationCollections Primary-File IR Handoff Evidence

The Foundation path advanced beyond configuration after staging SwiftSystem and
libdispatch, then reached the same OHOS-host Swift backend boundary seen in
stdlib, SwiftSystem, and libdispatch: direct `_FoundationCollections` object
emission crashes with signal 11.

Completed probes:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/configure-foundation-ohos-probe1-20260731-033718.log
CONFIG_RC=0

/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-foundation-ohos-probe1-j1-20260731-033842.log
direct _FoundationCollections object emission: signal 11

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

The bounded primary-file handoff emits the module once, then processes each
primary source through:

```text
swiftc -frontend -emit-ir -primary-file ...
opt -verify -disable-output
opt -S -strip-debug
/bin/sh toolchain/ohos-clang -target aarch64-unknown-linux-ohos -fPIC -c
```

All 155 primary files produced non-empty OHOS aarch64 relocatable
objects. This strengthens the Path B claim that the Swift toolchain adaptation
is an OHOS host/toolchain integration problem, not a normal package recipe
failure.

After the full handoff, the objects and Swift module were audited and archived:

```text
TOTAL=155
EXISTS_NONZERO=155
MODULE_OK=1
MISSING=0
ZERO=0
OUT=/storage/Users/currentUser/swift-mainline-ohos-src/build/foundation-ohos-probe1/lib/lib_FoundationCollections.a
OUT_SIZE=4267042
```

The larger `Foundation` target then advanced through C shims and Foundation ICU
C/C++ compilation before failing in `FoundationEssentials` semantic analysis.
This new boundary is distinct from the earlier object-emission crash:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-foundation-after-foundationcollections-j1-20260731-143809.log
FoundationEssentials/Platform.swift: cannot find 'secure_getenv' in scope
FoundationEssentials/FileManager/*: missing FTS/FTSENT/fts_* symbols
FoundationEssentials/Predicate/*.swift: macros are not supported in this compiler
FoundationEssentials/*Regex*.swift: cannot find Regex/RegexComponent in scope
```

Probe evidence shows why the Regex and concurrency-related Foundation code
cannot compile yet:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundation-frontend-features-20260731-145819.log
REGEX_RC=1
MACRO_RC=1
unable to perform implicit import of "_Concurrency" module: no such module found
unable to perform implicit import of "_StringProcessing" module: no such module found
```

The current mainline boundary is now missing Swift stdlib feature modules for
OHOS: `_Concurrency`, `_RegexParser`, `_StringProcessing`, and RegexBuilder are
present in the Swift source tree but absent from the current build graph. The
next Path B task is to enable/stage those stdlib modules with OHOS dependency
mapping before retrying FoundationEssentials and the SwiftPM/driver path.

## 2026-07-31 Stdlib feature-module staging evidence

The Swift 6.0.3 external string-processing repository was pinned to the
official release tag:

```text
swiftlang/swift-experimental-string-processing
swift-6.0.3-RELEASE
9c50f6da9be4b4a828cec31adbef758a6c3673d6
```

The source tree was transferred to the true device and unpacked at
`/storage/Users/currentUser/swift-mainline-ohos-src/deps/swift-experimental-string-processing-src`.
The archive sha256 was verified on both sides:

```text
19b615d31d904326bbb73fed9510524c66db3a00a7b133bc0fa2f681b48023b4
```

The existing OHOS Swift build was reconfigured with concurrency and string
processing enabled:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/reconfigure-swift-stdlib-concurrency-stringprocessing-20260731-161744.log
Concurrency Support:                ON
String Processing Support:          ON
Using Experimental String Processing library for _RegexParser
Using Experimental String Processing library for _StringProcessing
Using Experimental String Processing library for RegexBuilder
CMAKE_RC=0
```

Ninja target discovery then showed newly generated OHOS stdlib targets,
including `swift_Concurrency-ohos`, `swift_RegexParser-ohos`,
`swift_StringProcessing-ohos`, and `swiftRegexBuilder-ohos`. The first guarded
build is:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swift-Concurrency-ohos-j1-20260731-161949.log
nice -n 10 ninja -j1 swift_Concurrency-ohos
```

As of the first monitor window, the build is alive and resource-bounded. It is
rebuilding Swift compiler C++ dependencies first because the experimental
stdlib feature flags affect compiler-side conditionals; no new source failure
has been observed yet.

The first guarded run ended at the known backend object-emission boundary:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swift-Concurrency-ohos-j1-20260731-161949.log
[913/1041] Compiling .../stdlib/public/core/OHOS/aarch64/Swift.o
Running pass 'AArch64 Assembly Printer'
error: unable to execute command: Segmentation fault
error: compile command failed due to signal 11
NINJA_RC=1
```

Positive evidence from this run:

```text
[910/1041] Linking CXX executable bin/swift-frontend
```

So the experimental-flag compiler rebuild reached and linked a new frontend.
The remaining boundary is refreshing the Swift core object through the existing
IR handoff path under the new concurrency/string-processing flags. After the
failed edge, there were no residual Swift/ninja processes; the true device
showed about 14.5 GiB MemAvailable and 49.4 GiB SwapFree at
2026-07-31 18:40:24 CST.

## 2026-08-01 FoundationEssentials Full Handoff, Link, And Run Evidence

The Foundation path advanced from `_FoundationCollections` into
`FoundationEssentials` and reached a runnable minimal program.

Full primary-file IR handoff:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-primary-handoff-20260801-005338.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/foundationessentials-handoff-full-20260801-005338.status
FE_HANDOFF_REUSE_MODULE=1
clang_ok=182/182
status=0
real_errors=0
```

Output-file-map audit:

```text
filemap_records=182
objects_present=182
nonzero=182
missing=0
zero=0
objects_total_size=17241976
FoundationEssentials.swiftmodule size=3987972
```

The final shared-library link was isolated from `ninja -t commands` to avoid
rerunning the original dirty WMO edge. The first manual link showed the next
bootstrap boundary in `_FoundationCollections` archive symbols:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/run-foundationessentials-manual-link-20260801-022339.log
ld.lld: error: duplicate symbol: $s22_FoundationCollections9BigStringVSlAAMc
ld.lld: error: duplicate symbol: $s22_FoundationCollections9BigStringVSlAAWP
```

`llvm-nm` over `lib/lib_FoundationCollections.a` reported:

```text
defined_symbols=5573
duplicate_symbols=176
```

For bootstrap proof only, the final link was retried with
`-Xlinker --allow-multiple-definition`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/run-foundationessentials-link-allow-muldefs-20260801-022514.log
link_rc=0
output_exists=True
size=13426176
```

Dynamic dependency audit:

```text
Format: elf64-littleaarch64
Arch: aarch64
RUNPATH: /storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos::::::::
NEEDED: libswiftSwiftOnoneSupport.so
NEEDED: libswiftCore.so
NEEDED: libswift_Concurrency.so
NEEDED: libswift_StringProcessing.so
NEEDED: libswiftGlibc.so
NEEDED: libc.so
SONAME: libFoundationEssentials.so
```

Minimal true-device executable probe:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-exe-20260801-022741.log
source: import FoundationEssentials; Date(timeIntervalSinceReferenceDate: 0)
compile_rc=0
exe_exists=True
run_rc=0
stdout: 0
```

This is strong Path B evidence because the work crossed stdlib feature-module
staging, Foundation C shims, primary-file IR handoff, manual Ninja/link
recovery, dynamic dependency audit, and a true-device runtime probe. It is not
yet a final packaging solution: duplicate-symbol handling, RUNPATH cleanup,
macro support/guarding, and repeatable build-rule integration remain open
before retrying SwiftPM and `unxip`.

Follow-up reduced the duplicate-symbol boundary from a linker-wide
`--allow-multiple-definition` workaround to a targeted archive treatment. In
`lib_FoundationCollections.a`, only two duplicate symbols were strong:

```text
strong_duplicate_symbols=2
$s22_FoundationCollections9BigStringVSlAAMc  R,R
$s22_FoundationCollections9BigStringVSlAAWP  D,D
```

After weakening only those two symbols in a copy of the archive,
`FoundationEssentials` linked without `--allow-multiple-definition`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/run-foundationessentials-link-weaken-fc-validname-20260801-023624.log
link_rc=0
output_exists=True
size=13426176
```

The standard build-tree artifact path was switched to the weakened result and
revalidated:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-standard-exe-20260801-023951.log
compile_rc=0
run_rc=0
stdout: 0
```

This leaves a much cleaner Path B story: the remaining task is to formalize
duplicate strong-symbol detection/weakening in the IR-handoff archive rule
rather than relying on final-link `muldefs`.

RUNPATH cleanup was also validated. The malformed `::::::::` came from the
explicit empty rpath fragment in the final link command. Relinking without that
fragment produced a clean dynamic table:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/run-foundationessentials-link-clean-rpath-20260801-024228.log
link_rc=0
RUNPATH: /storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos
```

The clean-rpath so passed the executable probe:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-clean-rpath-exe-20260801-024307.log
compile_rc=0
run_rc=0
stdout: 0
```

The standard build-tree `lib/libFoundationEssentials.so` now points to the
clean-rpath, weakened-archive-linked artifact.

The archive weakening step was also folded back into the true-device helper
used by the patched Ninja rule:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/archive-foundationcollections-irhandoff-20260801-024636.log
OBJECTS=155
BAD=0
AR_RC=0
STRONG_DUPLICATES=2
WEAKEN_RC=0
STRONG_DUPLICATES=0
END_RC=0
```

So duplicate handling is now repeatable at the archive-helper level rather
than only as an interactive repair command.

The full `FoundationEssentials` handoff-to-link sequence was then captured in
a repeatable true-device helper:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/link_foundationessentials_from_handoff.py
/storage/Users/currentUser/swift-mainline-ohos-src/logs/link-foundationessentials-from-handoff-20260801-024854.log
COMMANDS=9
SKIP_ORIGINAL_WMO=1
END rc=0
RUNPATH: /storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos
```

The helper-installed standard artifact was validated by:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-after-helper-exe-20260801-024935.log
compile_rc=0
run_rc=0
stdout: 0
```

The next repeatability step integrated that handoff result into the generated
Ninja build tree for `FoundationEssentials`. Only the FoundationEssentials WMO
rule and final link variable were patched in the remote build tree, with
timestamped backups retained:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/build/foundation-ohos-probe1/CMakeFiles/rules.ninja.pre-fe-noop-20260801-030146.bak
/storage/Users/currentUser/swift-mainline-ohos-src/build/foundation-ohos-probe1/build.ninja.pre-fe-noop-20260801-030146.bak
```

The guarded run used `nice -n 10 ninja -j1 FoundationEssentials` and completed
successfully:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/ninja-foundationessentials-integrated-20260801-030348.log
BUILD_RC=0
ninja -n FoundationEssentials: no work to do
```

This is materially stronger than a one-off manual link: Ninja now records the
handoff outputs and considers the target clean without rerunning the unstable
direct Swift WMO object emission.

Dynamic table audit of the integrated shared object:

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

Fresh runtime probe:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-after-ninja-exe-20260801-030631.log
source: import FoundationEssentials; Date(timeIntervalSinceReferenceDate: 0)
compile_rc=0
run_rc=0
```

Operational guardrails were also kept: the run used `TMPDIR` under the writable
Swift probe root, single-job Ninja, and a monitor log. Start-of-run monitoring
reported about 13.26 GiB MemAvailable and 48.93 GiB SwapFree in:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/monitor-foundationessentials-integrated-20260801-030348.log
```

## FoundationInternationalization: repeatable handoff plus ICU loader boundary

The follow-up target `FoundationInternationalization` confirmed the same
general OHOS/aarch64 Swift compiler pattern: direct Swift object emission can
crash, while primary-file IR handoff through the OHOS LLVM fork remains viable.

Evidence:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-foundationinternationalization-j1-20260801-031425.log
direct WMO object emission: Swift frontend signal 11

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationinternationalization-primary-handoff-20260801-032408.log
primary-file IR handoff: 60/60 sources, 60 objects, rc=0

/storage/Users/currentUser/swift-mainline-ohos-src/logs/ninja-foundationinternationalization-integrated-20260801-035129.log
patched Ninja integration: BUILD_RC=0
ninja -n FoundationInternationalization: no work to do
```

The linked `libFoundationInternationalization.so` now has a clean local
Foundation RUNPATH and depends on `libFoundationEssentials.so`,
`lib_FoundationICU.so`, and the staged Swift OHOS runtime libraries.

The remaining blocker is runtime ICU loading:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationinternationalization-exe-20260801-035444.log
compile_rc=0
run_rc=127
```

Sampled ICU exports are present in `lib_FoundationICU.so`, including
`u_vformatMessage`, `ucal_getNow`, `udat_applyPattern`, `uloc_getLanguage`,
`ures_open`, and `ucol_open`. The dynamic audit instead points to loader-side
constraints:

```text
lib_FoundationICU.so RUNPATH: :::::::
lib_FoundationICU.so NEEDED: libc++_shared.so, libc.so
lib_FoundationICU.so has no .codesign section in the observed section table
libFoundationInternationalization.so has .codesign and a Foundation lib RUNPATH
```

This preserves the Path B evidence shape: the work has moved beyond a package
recipe fix into Swift/Foundation build-system surgery, frontend crash
workarounds, generated Ninja edge replacement, OHOS dynamic-loader auditing,
and signed runtime validation.

## Foundation main module: true-device smoke passed

The next resume closed the broader Foundation runtime boundary. The previous
`import Foundation` smoke had compiled but failed at runtime because
`libFoundation.so` referenced OHOS-missing
`posix_spawn_file_actions_addchdir`.

Evidence:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/repos/swift-corelibs-foundation/Sources/CoreFoundation/CFPlatform.c
OHOS probe patch: _CFPosixSpawnFileActionsChdir returns ENOSYS under defined(__OHOS__)

/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-Foundation-after-ohos-addchdir-j4-20260801-1215.log
nice -n 10 ninja -j4 Foundation
RC=0

/storage/Users/currentUser/swift-mainline-ohos-src/logs/sign-foundation-runtime-after-ohos-addchdir-20260801-1218.log
Foundation/dispatch runtime re-sign
RC=0

/storage/Users/currentUser/swift-mainline-ohos-src/logs/foundation-smoke-compile-20260801-121709.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/run-foundation-smoke-after-ohos-addchdir-20260801-1218.console.log
COMPILE_RC=0
RUN_RC=0
stdout: foundation-smoke 0
```

This is the strongest runtime evidence so far for the Path B/C Swift track:
the main OHOS-native Swift compiler, stdlib/runtime, libdispatch, Foundation
support libraries, and Foundation main module can now produce and run a minimal
true-device executable. It still remains a toolchain adaptation track rather
than a package recipe fix; `unxip` should stay paused until SwiftPM or an
equivalent Swift package build path is available.

## Swift new-driver prototype: version and target-info reached

The follow-up true-device stage moved from runtime libraries into the Swift
new-driver path that `unxip` will need before a package-level validation is
meaningful. The generated `swift-driver` CMake probe exposed the same OHOS
direct Swift object-emission crash class seen in stdlib and Foundation, so the
working route reused the primary-file IR handoff:

```text
swiftc -frontend -emit-module
swiftc -frontend -emit-ir -primary-file ...
opt -verify
opt -S -strip-debug
/bin/sh toolchain/ohos-clang -target aarch64-unknown-linux-ohos -fPIC -c
swiftc -emit-library / -emit-executable
```

True-device evidence:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftdriver-handoff-20260801-151610.log
SwiftDriver: 110/110 primary files, link_rc=0, lib_size=7929216

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftdriverexecution-handoff-20260801-161556.log
SwiftDriverExecution: 3/3 primary files, link_rc=0, lib_size=339328

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swift-driver-exe-handoff-20260801-164004.log
swift-driver executable: emit_ir_rc=0, objectize_rc=0, link_rc=0, exe_size=89600
```

The executable also exposed an OHOS runtime dependency boundary in
`libllbuildSwift.so`: `setupterm`, `tigetnum`, `set_curterm`, and
`del_curterm` are provided by the existing device library
`/storage/Users/currentUser/usr/local/lib/libtinfo.so.6`. The executable
handoff now links that provider and adds the user local library directory to
RUNPATH.

Runtime validation passed when the executable was invoked through an argv0
name that the driver recognizes. Because symlink creation is denied on the
tested filesystem, the probe used copied binaries under
`build/swift-driver-ohos-probe5/probe-bin/`:

```text
TMPDIR=/storage/Users/currentUser/swift-mainline-ohos-src/tmp
PATH=/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/bin:$PATH

probe-bin/swiftc -version
Swift version 6.0.3 (swift-6.0.3-RELEASE)
Target: aarch64-unknown-linux-ohos

probe-bin/swiftc -print-target-info
target.triple = aarch64-unknown-linux-ohos
```

Current boundary: the OHOS-native Swift 6.0.3 route now has a runnable
new-driver prototype for version and target-info. Remaining work before
returning to `unxip` is to formalize the IR handoff rules, clean temporary
probe logging, stabilize the `swiftc`/`swift` argv0 install strategy, stage
`swift-help`, build SwiftPM subcommands such as `swift-package` and
`swift-build`, and then use `unxip` as a Swift package validation case.

## Swift new-driver linker selection validated

The new-driver path moved beyond version and target-info into a real plain
compile/link/run test on the true device. A narrow OHOS experiment in
`SwiftDriver/Jobs/GenericUnixToolchain+LinkerSupport.swift` now selects the
real OHOS `clang-15` binary instead of the non-executable `clang` shell wrapper,
injects the staged OHOS sysroot when no SDK is passed, defaults OHOS links to
`lld`, and adds the required code-sign linker flag.

The validating rebuild completed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftdriver-handoff-20260801-181706.log
SwiftDriver: 110/110 primary files, link_rc=0, lib_size=7929216

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftdriverexecution-handoff-20260801-191242.log
SwiftDriverExecution: 3/3 primary files, link_rc=0, lib_size=339328

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swift-driver-exe-handoff-20260801-191435.log
swift-driver executable: emit_ir_rc=0, objectize_rc=0, link_rc=0, exe_size=89600
```

Validation used a fresh copied argv0 probe directory because the earlier
`probe-bin` files were not writable by the SSH user:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-bin-linkerpatch2-20260801-1916
```

With `SWIFT_DRIVER_CLANG_EXEC` unset and without passing explicit `-sdk` or
`-use-ld`, the new-driver probe passed:

```text
swiftc -version: rc=0, Swift 6.0.3, target aarch64-unknown-linux-ohos
swiftc -print-target-info: rc=0
swiftc -help: rc=0
```

The plain hello compile showed the intended automatic linker command:

```text
/storage/Users/currentUser/usr/local/bin/clang-15
-fuse-ld=lld
--sysroot /storage/Users/currentUser/usr/local/sysroot
-Wl,--code-sign
```

The executable compiled and ran:

```text
compile_rc=0
stdout: hello-new-driver-ohos
run_rc=0
```

This is a stronger Path B/C candidate signal than the earlier target-info
stage: the OHOS-native Swift route can now compile and link a simple program
through the Swift new driver without relying on an environment variable to
override the linker driver. Remaining package-level blockers are SwiftPM
entry points (`swift-package`/`swift-build`), reviewable source-level
integration of the IR handoff/linker patches, and cleanup of probe logging.

## 2026-08-01 SwiftPM dependency-chain evidence

The SwiftPM route advanced past simple driver validation into the package
manager dependency layer. SwiftPM configure exposed missing package config
files in order: SwiftASN1, SwiftCrypto, then SwiftCertificates. The OHOS-native
manual probes now provide these dependency-chain artifacts:

```text
SwiftASN1:
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftasn1-handoff-20260801-2143-foundation.log
emit_module_rc=0, 18/18 primary files, link_rc=0

SwiftCrypto Crypto:
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-crypto-handoff-20260801-2008.log
83/83 primary files, link_rc=0

SwiftCrypto _CryptoExtras:
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-cryptoextras-handoff-20260801-2055.log
11/11 primary files, link_rc=0

swift-certificates _CertificateInternals:
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-cert-_CertificateInternals-handoff-20260801-2109.log
link_rc=0
```

The SwiftASN1 probe also closed a cross-module feature boundary. The upstream
PEM implementation is conditionally compiled only when Foundation or
FoundationEssentials can be imported. Rebuilding SwiftASN1 with the staged
Foundation Swift module path and client C modulemaps made the PEM API visible:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/asn1-pem-smoke-20260801-215352.log
PEMDocument / PEMRepresentable / PEMSerializable / PEMParseable typecheck rc=0
```

This immediately unblocked the next swift-certificates `X509` probe:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-cert-X509-handoff-20260801-2155-pemfix.log
total_sources=99
emit_module_rc=0
```

The remaining evidence gap before using `unxip` is not the Swift driver or
Foundation startup anymore; it is completion of `X509`, regeneration or staging
of `SwiftCertificatesConfig.cmake`, and a runnable SwiftPM entry point
(`swift-package`/`swift-build`).

## 2026-08-02 SwiftPM entry points and HelloOHOS package smoke

The next true-device stage closed the first runnable SwiftPM-entry-point gap.
`swift-package` and `swift-build` now exist in the OHOS-native SwiftPM build
tree and both report Swift Package Manager 6.0.3.

Evidence:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/build/swiftpm-ohos-probe1/bin/swift-package
/storage/Users/currentUser/swift-mainline-ohos-src/build/swiftpm-ohos-probe1/bin/swift-build
Swift Package Manager - Swift 6.0.3
```

The work also reduced two earlier diagnostic runtime requirements:

- `PackageDescription` was copied beside the SwiftPM executables in
  `swiftpm-ohos-probe1/bin`, replacing the temporary
  `swiftpm-bin-manifestapi-copy-20260802-1045` shim for the direct SwiftPM
  smoke.
- `libllbuildSwift.so` was relinked with `-l:libtinfo.so.6`, so
  `llvm-objdump -p` now reports `NEEDED libtinfo.so.6`. This removes the
  previous `LD_PRELOAD=libtinfo.so.6` requirement; `/storage/Users/currentUser/usr/local/lib`
  still needs to be on the library search path.

Relink evidence:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/relink-llbuildswift-tinfo-linkonly-20260802-112804.log
lib/libllbuildSwift.so size: 8.5 MiB
lib/libllbuildSwift.so.bak-tinfo-20260802-112310 retained as backup
```

Minimal SwiftPM package smoke without preloading `libtinfo`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/swift-build-smoke-no-tinfo-preload-20260802-112915
Build complete! (21.32s)
Hello, world!
hello_rc=0
```

Direct `$SPM/bin` smoke after staging `PackageDescription` beside the
executables:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/swift-build-smoke-spmbin-20260802-113522
dump-package JSON size: 683 bytes
Build complete! (21.13s)
Hello, world!
hello_rc=0
```

The produced executable audits as an OHOS/aarch64 dynamic binary using the
OHOS musl interpreter and Swift runtime RUNPATH, with NEEDED limited to Swift
runtime libraries and `libc.so`.

Current boundary statement for Path B/C evidence:

- this is now beyond a "Swift missing on PATH" observation: the route includes
  OHOS-native Swift runtime, Foundation, Swift driver, SwiftPM dependency, and
  SwiftPM executable work;
- it is still not final toolchain delivery because package execution depends on
  a diagnostic concurrency/libdispatch hook, a diagnostic `swiftc -modulewrap`
  shim, manual SDK/resource-dir/modulemap flags, and SwiftCrypto diagnostic
  workarounds;
- `unxip` remains paused as a future validation package until the SwiftPM host
  toolchain path is formalized enough to build real SwiftPM packages with their
  non-Swift system dependencies.

## 2026-08-02 dispatch-backed SwiftPM evidence update

The SwiftPM path has moved beyond the earlier diagnostic
`LD_PRELOAD=libdispatch` concurrency hook. A dispatch-enabled
`libswift_Concurrency.so` was rebuilt and validated with the staged OHOS
libdispatch runtime:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-concurrency-dispatch-pic-uses-ninja-20260802-124248.log
NINJA_RC=0
```

The rebuilt runtime exports `swift_task_enqueueOnDispatchQueue`, contains the
`DispatchQueueShim` witness-table symbols, and records `NEEDED` entries for
`libdispatch.so` and `libBlocksRuntime.so`.

The next SwiftPM smoke no longer failed with:

```text
operation unsupported without libdispatch
DispatchQueueShim witness table missing
```

It instead exposed a manifest sysroot propagation boundary. The required CRT
and libc files exist under the OHOS sysroot, but the manifest compile command
omitted `-sdk`. A signed native ELF `swiftc` SDK wrapper proved the narrow fix:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/swiftc-modulewrap-sdkelf-20260802-1312/swiftc
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-dump-sdkelf-20260802-1318.log
RC=0
```

With that wrapper and `--disable-index-store`, SwiftPM can now build and run
debug-mode packages without the concurrency preload:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-build-sdkelf-noindex-20260802-1328.log
Build complete! (23.40s)

/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-run-audit-sdkelf-20260802-1333.log
hello swiftpm ohos
```

An async SwiftPM smoke using `async main` and `Task.yield()` also builds and
runs:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-async-build-run-sdkelf-20260802-1400.log
Build complete! (28.52s)
async swiftpm ohos
```

This is strong Path B/C evidence because it crosses multiple layers at once:
OHOS-native Swift runtime, dispatch-backed concurrency, SwiftPM manifest
compilation, SwiftPM target compilation, OHOS linker/signing behavior, and
runtime execution. It is still candidate evidence, not a final delivered
toolchain, because it depends on generated Ninja patches, a signed SDK wrapper,
`--disable-index-store`, and a diagnostic modulewrap shim. The optimized
SwiftPM release path remains blocked by a Swift frontend `-O` crash.

## 2026-08-02 index-store boundary reduced

The SwiftPM default-index-store blocker has been experimentally removed from
the debug validation path. A narrow frontend rebuild filtered
`-index-store-path` out of OHOS ClangImporter driver arguments:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/rebuild-swiftfrontend-indexstore-20260802-133739.log
RC=0
```

With the patched frontend, SwiftPM no longer needs `--disable-index-store` for
the debug smoke, as long as the still-manual OHOS SDK/resource-dir/Glibc
modulemap arguments are passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-indexstore-xswiftc-20260802-135449.log
Build complete! (21.56s)
index store xswiftc ohos
RC=0

/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-async-indexstore-xswiftc-20260802-140136.log
Build complete! (29.09s)
async index store xswiftc ohos
RC=0
```

This is a meaningful Path B/C increment because it turns one validation-only
workaround into a source-level frontend behavior change. The remaining
toolchain delivery boundaries are now clearer:

- SwiftPM still needs first-class OHOS SDK/resource-dir/modulemap propagation;
- dispatch libraries need repeatable runtime staging instead of manual copies;
- `swiftc -modulewrap` still crashes after writing the object and is currently
  masked by the diagnostic wrapper;
- release/optimized SwiftPM compilation still crashes in the Swift frontend
  `-O` path;
- `unxip` remains paused until these toolchain supports are formalized enough
  for a real package validation run.

## 2026-08-02 release IR handoff evidence

Release-mode SwiftPM was split into frontend and link responsibilities. The
direct release frontend matrix shows that optimized SIL generation is usable,
optimized IR can be emitted as a non-empty artifact, and the remaining direct
object path fails in backend object emission:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/release-frontend-variants-20260802-141443.log
```

The follow-up handoff used that release IR as the boundary and successfully
finished the rest of the native OHOS flow:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/release-irhandoff-link-20260802-141640.log
CLANG_RC=0
LINK_RC=0
RUN_RC=0
stdout: release xswiftc ohos
```

This raises the confidence of the Path B/C candidate because optimized Swift
code can now be turned into a runnable OHOS executable through a known
handoff. The delivery gap is making the handoff repeatable and reviewable
inside the Swift build/driver path, rather than keeping it as a manual
diagnostic sequence.

## 2026-08-02 default SDK propagation evidence

The SwiftPM debug path no longer needs the earlier signed SDK ELF wrapper for
basic SDK propagation. A narrow SwiftDriver experiment was rebuilt on the true
device so `linux-ohos` can derive a default SDK path from `OHOS_SDKROOT`,
`OHOS_SYSROOT`, or `SDKROOT`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swift-driver-defaultsdk-j1-20260802-1506.log
NINJA_RC=0
link_rc=0
```

After using the matching SwiftPM/SwiftDriver dependency library search path, a
fresh pure SwiftPM package built and ran through `$MAN/bin/swift build` without
manual `-Xswiftc -sdk` flags:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-default-defaultsdk-swiftbuild-20260802-164449.log
Build complete! (84.22s)
BUILD_RC=0
RUN_RC=0
stdout: default sdk swift build ohos
```

The same path then passed a stronger package smoke importing Glibc:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-glibc-defaultsdk-swiftbuild-20260802-165044.log
Build complete! (112.40s)
BUILD_RC=0
RUN_RC=0
stdout: glibc default sdk pid 46298
```

The logs show `-sdk /storage/Users/currentUser/usr/local/sysroot` on Swift
frontend manifest/target commands, `--sysroot` in ClangImporter and link
commands, and `-lswiftGlibc` plus `NEEDED libswiftGlibc.so` for the Glibc
executable. This materially reduces the SwiftPM integration boundary: SDK and
Glibc import propagation have been proven through the driver source path for
debug packages. The remaining Path B/C delivery work is cleanup and
formalization: reviewable SwiftDriver/SwiftPM patches, dispatch runtime staging,
replacement of the modulewrap diagnostic shim, and a repeatable release
IR-to-object strategy.

## 2026-08-02 SwiftPM release package smoke through signed IR handoff

The latest true-device release probe moved beyond the earlier manually split
release link and exercised a complete SwiftPM release build for a fresh package
that imports Glibc. The diagnostic wrapper was:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/swift-irhandoff-wrapper-sdkfix-20260802-190734
```

The wrapper turns optimized frontend object emission into a repeatable
diagnostic sequence: emit non-empty IR, tolerate the current post-IR frontend
signal 5/RC 133, strip debug metadata, objectize with OHOS `clang-15`, inject
the OHOS SDK/modulemap search paths, and keep final links on the signed OHOS
`clang-15`/`ld.lld` path.

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-release-irhandoff-sdkfix-20260802-191210.log
Build complete! (112.19s)
BUILD_RC=0
stdout: swiftpm release sdkfix pid 23011
RUN_RC=0
```

The executable audit shows the expected OHOS loader and runtime dependency
surface:

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

This is strong Path B/C evidence: the remaining obstacle is not whether SwiftPM
release packages can produce runnable OHOS binaries, but how to upstream or
otherwise formalize the IR handoff, modulewrap behavior, SDK propagation, and
runtime signing without relying on temporary wrappers.

## 2026-08-02 controlled concurrency evidence

The release frontend boundary was narrowed further. Direct optimized object
emission can sometimes write valid ELF relocatable objects before exiting with
signal 5/RC 133, and those objects can autolink, link, and run:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-release-direct-debugmeta-link-20260802-192948.log
debug: AUTOLINK_RC=0 LINK_RC=0 RUN_RC=0
gnone: AUTOLINK_RC=0 LINK_RC=0 RUN_RC=0
```

However, a full SwiftPM release package using an "accept valid ELF object"
wrapper still failed when the frontend produced a zero-byte object with RC 139:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-release-validobj-sdkfix-j2-20260802-193829.log
BUILD_RC=1
RUN_RC=127
[ohos-validobj] frontend rc=139 valid_elf=0
```

This rules out treating non-zero frontend exits as a general solution. The
repeatable release path remains IR handoff to the OHOS LLVM backend.

The same IR handoff wrapper then passed a full SwiftPM release Glibc smoke with
package concurrency raised to `-j 2` and frontend WMO threads explicitly capped
at 2:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-release-irhandoff-sdkfix-j2-t2-20260802-194542.log
Build complete! (112.51s)
BUILD_RC=0
stdout: swiftpm release irhandoff j2 t2 pid 12531
RUN_RC=0
```

This is useful operational evidence for Path B/C: higher concurrency is safe
when monitored and when Swift frontend internal thread counts are controlled,
but release-mode correctness still depends on formalizing the IR handoff.

A stronger package-shape check then passed with SwiftPM `-j 3` and an explicit
frontend thread cap of 3. The package had three library targets plus one
executable target, all built in release mode through the IR handoff wrapper:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-release-irhandoff-multitarget-j3-t3-20260802-195322.log
Build complete! (166.72s)
BUILD_RC=0
stdout: swiftpm release multitarget j3 t3 138
RUN_RC=0
```

Monitoring stayed safe with the lowest sampled `MemAvailable` around 13.7 GiB
and `SwapFree` around 49.5 GiB. This supports using `j3` for bounded SwiftPM
package probes on the current true device, while keeping a monitor and explicit
frontend thread controls in place.

The front-door entry point was also validated. A first `$MAN/bin/swift build`
attempt failed immediately with `error: unable to invoke subcommand:
swift-build (No such file or directory)`, proving that the current toolchain
layout still needs SwiftPM subcommand installation or PATH integration. After
placing `$SPM/bin` on `PATH`, the same multi-target release package passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swift-man-build-release-multitarget-pathfix-j3-t3-20260802-200448.log
Build complete! (167.69s)
BUILD_RC=0
stdout: swift frontdoor pathfix release j3 t3 85
RUN_RC=0
```

This moves the evidence from a diagnostic `swift-build` binary toward the
standard `swift build` user workflow, while preserving the remaining packaging
boundary as an explicit item.

## 2026-08-02 unxip-specific Swift package boundary

After SwiftPM release mode passed controlled `j2/t2` and `j3/t3` package
smokes, `unxip/3.3` was used as the next real package probe. The source archive
was staged on the true device, and the upstream symlink
`Sources/libunxip/libunxip.swift -> ../../unxip.swift` had to be materialized
as a normal file because the tested OHOS extraction path does not create that
link.

The unxip build now reaches real Swift source imports. With only the current
SwiftPM toolchain path, it fails at plain Foundation lookup:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/unxip-swiftpm-release-product-j3-t3-20260802-202917.log
error: no such module 'Foundation'
```

Adding the staged Foundation Swift module path moves the boundary forward but
does not yet produce an unxip binary:

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

The current interpretation is:

- `GNUSource`, `getopt`, and `zlib` are importable.
- `Foundation` itself is usable when its Swift module directory and client C
  module maps are supplied. A direct Foundation executable probe passed with
  `RC_COMPILE=0` and `RC_RUN=0` in
  `/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundation-cmodule-paths-20260802-210746.log`.
- `lzma` is blocked by missing `lzma.h`; this belongs to the `xz`/liblzma
  dependency boundary and should not be patched inside the unxip PR.
- `FoundationXML` is not built or staged in the current Foundation build
  because the first Foundation pass used `FOUNDATION_ENABLE_XML=OFF`.

The FoundationXML route is now partially de-risked. Turning XML on without a
header path failed with:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/configure-foundation-xml-probe1-20260802-211222.log
Could NOT find LibXml2 (missing: LIBXML2_INCLUDE_DIR)
```

The existing Conan cache already provides the published `libxml2/2.15.3`
package with headers and `libxml2.so`. Feeding those paths to CMake generated a
valid Foundation XML build graph:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/configure-foundation-xml-probe2-20260802-212033.log
Found LibXml2: .../lib/libxml2.so (found version "2.15.3")
CONFIG_RC=0
```

The generated graph contains `_CFXMLInterface`, `FoundationXML.swiftmodule`,
and `libFoundationXML.so`, but a fresh build directory would rebuild 574 steps
before completing `FoundationXML`. The next efficient path is to seed or reuse
the validated Foundation artifacts and only compile `_CFXMLInterface` plus the
seven `FoundationXML` Swift sources under the same monitored `j2`/`j3`
discipline.

This update strengthens the high-difficulty claim: unxip is no longer blocked
by absence of any Swift executable. It is now exercising staged SwiftPM release
mode, Foundation client module maps, FoundationXML/libxml2 integration, OHOS
archive link handling, and the separate `xz` header dependency boundary.

## 2026-08-02 Direct unxip Binary Evidence

The FoundationXML boundary has been reduced from "missing module" to a staged
runtime integration task. `_CFXMLInterface` plus the seven FoundationXML Swift
sources were built by reusing the validated Foundation artifacts, then
`libFoundationXML.so` was linked and signed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/foundationxml-irhandoff-20260802-214017.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/relink-foundationxml-probe2-20260802-214626.log
LINK_RC=0
SIGN_RC=0
```

`import FoundationXML` typechecking passed with the generated libdispatch module
map and VFS overlay, and executable smokes passed for both an import-only case
and an `XMLDocument` parse case:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/verify-foundationxml-import-ninjadispatch-20260802-215708.log
TYPECHECK_RC=0

/storage/Users/currentUser/swift-mainline-ohos-src/logs/verify-foundationxml-import-only-exe-20260802-220216.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/verify-foundationxml-xmldoc-exe-20260802-220452.log
COMPILE_RC=0
SIGN_RC=0
RUN_RC=0
stdout: toc
```

The `xz/5.6.2` Conan cache package supplies the lzma development surface:

```text
/storage/Users/currentUser/.conan2/p/xz22c09c364bc26/p/include/lzma.h
/storage/Users/currentUser/.conan2/p/xz22c09c364bc26/p/lib/liblzma.a
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-lzma-import-with-xz-cache-env-20260802-221415.log
TYPECHECK_RC=0
```

With those staged paths, full direct `unxip` typechecking passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/typecheck-unxip-direct-parseaslib-20260802-222300.log
TYPECHECK_RC=0
```

The normal SwiftPM package route still has a process-boundary blocker:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/unxip-spm-release-irhandoff-j2-20260802-223538-b64.log
swift-build slept in do_rt_sigsuspend with no frontend child and no log growth.
BUILD_STOPPED_BY_CODEX
```

However, the same code base was compiled directly with Swift 6 in optimized mode
through the proven OHOS IR handoff and produced a runnable `unxip` executable:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/unxip-direct-swiftc-irhandoff-concurrencyfix2-20260802-225605.log
[ohos-irhandoff] emit-ir rc=0 size=3656085
[ohos-irhandoff] opt rc=0
[ohos-irhandoff] clang rc=0 object-size=903152
BUILD_RC=0
SIGN_RC=0
HELP_RUN_RC=0
```

The resulting executable uses the OHOS musl loader and depends on the staged
Swift/Foundation/Dispatch/XML runtime surface, including `libFoundationXML.so`,
`libFoundation.so`, `libswiftDispatch.so`, `libdispatch.so`, `libz.so`,
`libxml2.so.16`, Swift runtime libraries, and `libc.so`.

This is stronger evidence than the initial Path B claim. The current work has
proven a real Swift package executable can be built for OHOS; what remains is
reviewable integration of the SwiftPM process path and replacement of diagnostic
wrappers with source-level Swift driver/frontend/build-system behavior.

## 2026-08-02 SwiftPM unxip release success

The earlier `swift-build` pause was reclassified as a timeout/observation
boundary, not a confirmed permanent hang. A monitored single-job SwiftPM release
run completed the full `unxip` package:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/unxip-spm-release-irhandoff-longmon-j1-t1-20260802-234731.log
Build complete! (211.85s)
[ohos-irhandoff] emit-ir rc=133 size=5863471
[ohos-irhandoff] opt rc=0
[ohos-irhandoff] clang rc=0 object-size=699192
```

The generated binary exists under the normal SwiftPM release directory and
passes the CLI help smoke on the true device:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/unxip-3.3-src/.build/aarch64-unknown-linux-ohos/release/unxip
HELP_RC=0
```

This materially strengthens the Path B/C candidate evidence. The current work
has crossed SwiftPM manifest execution, target compilation, FoundationXML,
libdispatch, zlib/xz/libxml2 staging, optimized IR handoff, link, runtime
loading, and CLI execution for a real upstream package. It still should not be
presented as a clean final toolchain or Conan CI pass: the path relies on
experimental wrappers/source patches and needs formalized SwiftDriver, SwiftPM,
frontend, modulewrap, signing, runtime staging, and recipe integration.

## 2026-08-03 Conan recipe integration evidence

The unxip recipe has now been exercised through true-device Conan packaging
using the experimental OHOS-native Swift 6.0.3 path. The first Conan build
showed one additional Swift 6 source compatibility site in
`PermissiveActionLink.next()`, and the recipe now patches that continuation
shape in both `unxip.swift` and the materialized `Sources/libunxip` source.

Full source-build/package log:

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

Created package:

```text
unxip/3.3@ohpcd/stable#f9fcc576fbe5befb3433e94facae4f04:15141ce3eb5a91ba7d0b3075840da216efff4f0c#e6fb8470213a704b353d7c0a80add145
/storage/Users/currentUser/.conan2/p/b/unxip07ec4440ee2f8/p/bin/unxip
sha256 a69bed8143713233b985478e77335dbace16751113c6d4b677282a6f83be505c
```

The initial test_package failure was not a Swift or runtime failure; it was a
fixed shell-path assumption:

```text
/system/bin/sh: /data/service/hnp/bin/bash: inaccessible or not found
```

After making the test package select an available shell and making `test.sh`
POSIX-sh compatible, standalone `conan test` passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/conan-test-unxip-swiftpm-irhandoff-20260803-0104-test.out
unxip 3.3
TEST_RC=0
```

A final cached full `conan create` rerun also completed test_package:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/conan-create-unxip-swiftpm-irhandoff-20260803-0105-full-create.out
unxip/3.3@ohpcd/stable (test package): Running test()
unxip 3.3
CREATE_RC=0
```

Package-level runtime smokes passed:

```text
unxip --version -> unxip 3.3, VERSION_RC=0
unxip --help -> HELP_RC=0
```

`llvm-objdump -p` on the packaged binary reports `/lib/ld-musl-aarch64.so.1`,
RUNPATH to the staged Swift/Foundation/Dispatch runtimes and Conan libxml2/xz
package paths, and NEEDED entries for Swift runtime libraries, Dispatch,
Foundation/FoundationXML, and `libc.so`.

This moves unxip itself from "Conan integration pending" to "true-device Conan
create/test_package proven under the experimental Swift path". The high
difficulty boundary remains at the toolchain layer: formalizing or publishing
SwiftDriver/SwiftPM/frontend IR handoff, modulewrap, SDK/resource propagation,
runtime staging, and signing so the result is reproducible in clean CI without
probe-only wrappers or absolute staged runtime paths.
