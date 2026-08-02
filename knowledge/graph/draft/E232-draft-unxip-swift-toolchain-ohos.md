# E232: Swift Linux aarch64 Toolchain Tarball On OHOS

> Status: DRAFT | Created: 2026-07-25 | Source: `unxip/3.3`

## Symptom

A SwiftPM package such as `unxip/3.3` reaches Conan `build()` on HarmonyOS PC
but cannot start compilation:

```text
ConanException: Swift 6 toolchain not found on PATH
```

Trying an official Swift Linux/aarch64 toolchain tarball directly on the device
does not immediately solve the problem. The probe observed:

```text
tar: can't link '.../usr/bin/swift' -> 'swift-driver': Permission denied
tar: can't link '.../usr/bin/swiftc' -> 'swift-driver': Permission denied
```

Running an extracted real binary before signing returned:

```text
swift-driver: Permission denied
```

After signing `swift-driver`, the error changed to:

```text
swift-driver: No such file or directory
```

## Root Cause

The official Swift Linux/aarch64 tarball is built for a Linux/glibc userspace,
not directly for OHOS. The binary requests the Linux dynamic interpreter:

```text
/lib/ld-linux-aarch64.so.1
```

The same binary also needs glibc-era runtime libraries such as:

```text
libc.so.6
libm.so.6
libstdc++.so.6
libgcc_s.so.1
libncurses.so.6
libtinfo.so.6
libsqlite3.so.0
```

Swift's own libraries are located through:

```text
$ORIGIN/../lib/swift/linux
```

Swiftly is a separate official installer/manager source. A local static
inspection of `https://download.swift.org/swiftly/linux/swiftly-aarch64.tar.gz`
showed the extracted `swiftly` executable has no `PT_INTERP` and no dynamic
section, so it can be used as a low-cost future probe. It does not prove the
installed Swift compiler can run, because Swiftly is expected to install the
official Linux Swift toolchains unless another target is selected.

True-device follow-up confirmed the distinction:

- unsigned Swiftly fails with `Permission denied`;
- after signing and preserving the executable name as `swiftly`, `--help`
  works;
- stock `swiftly init --skip-install` fails because no system
  `ca-certificates` bundle is installed and `SSL_CERT_FILE` does not bypass
  Swiftly's hard-coded preflight check;
- a probe-only same-length path patch from
  `/etc/pki/tls/certs/ca-bundle.crt` to `/storage/Users/currentUser/a.pem`,
  followed by re-signing, lets
  `swiftly init --platform ubuntu22.04 --skip-install` succeed;
- `swiftly list-available` then lists Swift 6.0.3, but no Swift compiler
  toolchain was installed in this probe.

The 2026-07-26 follow-up resumed the install probe. Swiftly downloaded the full
Swift 6.0.3 Ubuntu 22.04 aarch64 toolchain (`735.9 MiB`) but failed during
extraction:

```text
Error: ExtractError(message: Optional("Can't create '.../usr/bin/aarch64-swift-linux-musl-clang++.cfg'"))
```

The failing entry corresponds to the archive's link-style config file
`aarch64-swift-linux-musl-clang++.cfg -> aarch64-swift-linux-musl-clang.cfg`.
This adds a second Swiftly boundary after CA handling: OHOS filesystem/archive
link behavior must be handled before an installed `swift` binary can be
inspected or signed.

The 2026-07-26 04:00 follow-up flattened the minimum link-style entries in the
partially extracted Swift 6.0.3 toolchain:

```text
swift -> swift-driver
swiftc -> swift-driver
clang -> clang-17
aarch64-swift-linux-musl-clang++.cfg -> aarch64-swift-linux-musl-clang.cfg
```

This allowed direct ELF inspection and execution attempts. The flattened
`swift` binary still requested `/lib/ld-linux-aarch64.so.1`, plus glibc-family
runtime libraries such as `libc.so.6`, `libm.so.6`, `libstdc++.so.6`, and
`libgcc_s.so.1`. Signing `swift` and `swift-frontend` did not make them run;
both still failed with `No such file or directory`. Link-flattening is therefore
necessary for archive handling, but insufficient for OHOS execution.

The glibc runtime bundle probe refined the conclusion. A minimal Ubuntu 22.04
arm64 runtime bundle was assembled from official packages and symlinks were
materialized as normal files. The signed `ld-linux-aarch64.so.1` loader itself
can run and print help on OHOS. However, running `swift`, `swift-frontend`, or a
minimal Ubuntu `coreutils` `true` binary through that signed loader fails with:

```text
failed to map segment from shared object
```

This means the user-space glibc bundle route is not sufficient. The blocker is
not just that `/lib/ld-linux-aarch64.so.1` is absent; loader-mediated mapping of
Linux/glibc executable segments fails on the tested OHOS environment even when
the loader and target executable are signed.

The tested `/storage/Users/currentUser` mount does not show an explicit
`noexec` flag, and signed Swiftly plus signed `ld-linux-aarch64.so.1` can start
from the same probe area. Direct execution of signed Ubuntu `true` still reports
`No such file or directory` because of its Linux PT_INTERP; running through the
signed loader reaches `failed to map segment from shared object`. Treat this as
a loader-mediated mapping or compatibility-layer boundary, not a simple
directory noexec issue.

OHOS does not provide `/lib/ld-linux-aarch64.so.1` in the tested environment.
That is why a signed binary still fails with `No such file or directory`: the
kernel cannot resolve the requested interpreter.

## Reproduction

Official toolchain tested:

```text
https://download.swift.org/swift-6.0.3-release/ubuntu2204-aarch64/swift-6.0.3-RELEASE/swift-6.0.3-RELEASE-ubuntu22.04-aarch64.tar.gz
```

Device checksum:

```text
0ce755e7ed16fa07f6d1207a8135aff97e977653c1359011c60cb6d85a9cfa5b
```

Minimal probe:

```sh
tar -tzf swift-6.0.3-RELEASE-ubuntu22.04-aarch64.tar.gz | head
tar -xzf swift-6.0.3-RELEASE-ubuntu22.04-aarch64.tar.gz -C extract

SWIFT_DRIVER=extract/swift-6.0.3-RELEASE-ubuntu22.04-aarch64/usr/bin/swift-driver
$HOME/usr/local/bin/llvm-readobj --program-headers --dynamic-table "$SWIFT_DRIVER"
$HOME/usr/local/bin/binary-sign-tool sign \
  -inFile "$SWIFT_DRIVER" \
  -outFile "$SWIFT_DRIVER.signed.tmp" \
  -selfSign 1
mv "$SWIFT_DRIVER.signed.tmp" "$SWIFT_DRIVER"
"$SWIFT_DRIVER" --version
```

## Recommendation

Do not hide Swift toolchain migration inside a Swift package recipe. Treat it as
a separate prerequisite:

1. Keep the package recipe honest: fail clearly when `swift` is absent.
2. Record that normal Conan dependencies are already published.
3. Open a dedicated Swift toolchain exploration task/issue if SwiftPM packages
   are in scope.
4. Evaluate whether a true OHOS Swift host toolchain exists, or whether a
   platform-approved Linux/glibc compatibility layer can run at least a minimal
   Ubuntu/glibc executable before Swift is retried.
5. Probe the static Swiftly aarch64 installer separately from the compiler it
   installs.
6. If Swiftly is used, provide a system-level CA bundle or an approved Swiftly
   patch before installing toolchains.
7. Handle Swift toolchain archive link extraction on OHOS before expecting
   `swiftly install` to register a complete toolchain.
8. Treat `/lib/ld-linux-aarch64.so.1` as the next hard boundary after
   link-flattening; a true OHOS Swift host toolchain or approved Linux/glibc
   runtime strategy is required.
9. Do not assume bundling glibc libraries is enough. First prove that a signed
   glibc loader can map and run a minimal Linux/glibc executable; the current
   probe shows it cannot.
10. Revisit Swift static Linux SDK only after the host `swift` executable can run
   on the device.
11. For the mainline path, first verify the OHOS-native C/C++ substrate, then
    plan a staged Swift bootstrap: Linux-host Swift with OHOS target support,
    OHOS runtime/stdlib build, OHOS-host Swift tools, signing, and finally
    `swift --version` on the device. The current true-device smoke shows
    `clang-15` can build and run C/C++ OHOS executables when `TMPDIR` is
    writable, but Swift-specific target/runtime/bootstrap work is still missing.
12. A 2026-07-28 Swift 6.0.3 source-build probe on the true device has advanced
    through multiple LLVM15 compatibility layers: IRGen memory effects,
    TextAPI/TBD symbol kinds and flags, and disabled-but-compilable LLVM CAS
    shims. The latest synced CAS fixes cover `CASID` overloads,
    `ObjectProxy` data conversion, `AsyncProxyValue::take`, and `CASID` stream
    printing. The rebuild passed the previous
    `CachingUtils.cpp`/`CompileJobCacheResult.cpp` boundary, relinked
    `libswiftAST.a` and `libswiftSIL.a`, and reached `[270/807]` in `lib/Sema`.
    A later resume linked `libswiftSema.a`, entered `SILGen` and
    `SILOptimizer`, and reached `[139/537]` (about `[409/807]` in the original
    graph). A further resume entered `IRGen` and reached `[218/398]` at
    `lib/IRGen/GenClangType.cpp.o` before another manual resource-scheduling
    pause for a true-device heavy task. Later Frontend resumes validated the
    `CompilerInvocation.cpp` CAS/optional fixes, added the missing Clang
    serialized-diagnostics `RECORD_SOURCE_FILE_CONTENTS` record, compiled
    `SerializedDiagnosticConsumer.cpp`, and linked `libswiftIRGen.a`. The next
    boundary is `SWIFT_USE_SYMLINKS=ON` on an OHOS filesystem that rejects
    `cmake -E create_symlink`; reconfigure with `SWIFT_USE_SYMLINKS=OFF` before
    continuing. Do not retry package-level SwiftPM CI until a signed OHOS
    `swift` or `swift-frontend` binary is produced and passes runtime checks.
13. A 2026-07-29 CST follow-up produced OHOS-runnable `swift`, `swiftc`, and
    `swift-frontend` binaries. `swift --version` reports Swift 6.0.3 with target
    `aarch64-unknown-linux-ohos`. The remaining blocker is now clean-cache
    `import SwiftShims`: Clang starts building the SwiftShims PCM, reaches
    `FrontendAction::CreateWrappedASTConsumer`, then traps with `RC=133` before
    the older marker at `setASTMutationListener`. If the crash leaves
    `SwiftShims.pcm` in the cache, a cache-reuse probe can pass. This points at
    first-time Clang module/PCM creation or finalization, not host executable
    startup. Further markers around Consumer null-check, `isModelParsingAction`,
    `GetASTMutationListener`, and `setASTMutationListener` were synced to the
    true-device LLVM source and are waiting for the next free-device rebuild
    window.
14. The latest clean-cache `SwiftShims` probe narrowed the trap to the Clang
    object PCH container backend: `PCHGenerator::Writer.WriteAST` completes,
    then `ObjectFilePCHContainerGenerator` reaches
    `clang::EmitBackendOutput(... Backend_EmitObj ...)` and traps before the
    next marker. A minimal Swift ClangImporter experiment has been synced to the
    true-device source to select raw PCM containers for OHOS targets and skip
    `ObjectFilePCHContainerWriter/Reader`. Rebuild and verification are pending
    because the true device was occupied by an `apache-arrow-glib` `make -j20`
    build at 2026-07-29 16:13 CST.
15. The raw PCM experiment was then rebuilt and validated on the true device:
    `swift-frontend` rebuilt with `RC=0`, clean-cache `import SwiftShims`
    completed with `RC=0`, and `swiftCore-swiftmodule-ohos-aarch64` completed
    with `RC=0`. This produced the OHOS/aarch64 `Swift.swiftmodule` and
    `Swift.swiftdoc` files. The next target is `swiftCore-ohos-aarch64` for
    `libswiftCore.so`; it was deferred because other true-device heavy tasks
    restarted.
16. A 2026-07-30 CST follow-up completed `swiftCore-ohos-aarch64` on the true
    device. Direct `Swift.o` emission crashed in LLVM's AArch64 assembly
    printer, but the same frontend invocation could emit a 94 MiB `Swift.ll`.
    Compiling that IR with the OHOS LLVM fork's `clang-15` produced a 20 MiB
    aarch64 relocatable `Swift.o`. A narrow remote build-tree `swiftc` wrapper
    was used to make Ninja record this IR-to-object path for the stdlib
    `Swift.o` edge. The next link then exposed missing PIC on runtime/support
    object targets; adding `-fPIC` to 95 OHOS/aarch64 runtime/support compile
    edges in generated `build.ninja` allowed
    `build-swiftCore-ohos-aarch64-pic-runtime-20260730-115544.log` to complete
    with `RC=0`, producing
    `lib/swift/ohos/aarch64/libswiftCore.so` as a 34 MiB aarch64 ELF shared
    object. These are still experimental build-tree workarounds; a source-level
    fix should move the IR/object strategy and PIC propagation into Swift/CMake
    patches.
17. The next broad-stdlib blocker is Platform/Glibc overlay generation for
    OHOS. `stdlib/swift-stdlib-ohos-aarch64` referenced
    `swiftGlibc-swiftmodule-ohos-aarch64`, but
    `stdlib/public/Platform/CMakeLists.txt` did not include OHOS in the
    `swiftGlibc` target SDK list or in `glibc.modulemap` generation. A remote
    source experiment added OHOS to those paths, excluded OHOS from the
    `glibc.modulemap.gyb` `link "dl"` rule, and generated the OHOS
    `glibc.modulemap` plus `SwiftGlibc.h`. Follow-up probes showed three
    required source/environment fixes: set `TMPDIR` to a writable user
    directory for Swift driver supplementary outputs; point
    `SWIFT_SDK_OHOS_ARCH_aarch64_PATH` at the real staged OHOS sysroot instead
    of `/`; and guard `LibcOverlayShims.h` semaphore wrappers with
    `__has_include(<semaphore.h>)` because the tested OHOS sysroot lacks
    `semaphore.h`. With those applied, the sysroot rerun reached at least
    `[471/916]` without a compile failure, then the true device entered
    sustained memory pressure and SSH commands reported `Out of memory` or
    `can't fork`. Treat this as a resource boundary pending final remote-state
    confirmation, not as a confirmed Swift source failure.
18. A 2026-07-30 14:56 CST recovery check found the original Swift build host
    pingable but unreachable over both direct SSH `10.62.230.12:2222` and the
    old-O SakuraFrp tunnel `frp-tip.com:56267`. The second O machine
    `frp-tip.com:33332` was reachable, but it did not contain
    `/storage/Users/currentUser/swift-mainline-ohos-src`, so it cannot resume
    the current incremental Swift build without a fresh source/build-tree
    transfer. No new source failure is implied by this connection boundary.

## Applicability

This pattern applies to SwiftPM packages that require a host Swift toolchain on
HarmonyOS PC, especially packages with `Package.swift` and
`swift-tools-version:6.x`.

It does not apply to C/C++ packages that only depend on Swift ecosystem libraries
such as `swift-corelibs-libdispatch`; those may be adapted as ordinary CMake or
library recipes when they do not require the Swift compiler.

## 2026-07-30 Evening SwiftGlibc/Stdlib Update

The OHOS SwiftGlibc overlay advanced past the missing-module boundary. Adding
the generated OHOS `glibc.modulemap` explicitly with
`-Xcc -fmodule-map-file=.../lib/swift/ohos/aarch64/glibc.modulemap` changed the
failure from `no such module 'SwiftGlibc'` to real modulemap/header issues. The
current remote experiment resolves `assert.h` through the staged OHOS sysroot,
removes the unavailable `CUUID` block, and avoids glibc-private
`__sighandler_t` by defining OHOS `sighandler_t` as a C function pointer.

The proof target passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swiftGlibc-swiftmodule-ohos-aarch64-flags-20260730-184945.log
RC=0
```

The next full-chain run is:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-stdlib-ohos-aarch64-full-j1-20260730-191240.log
```

It is running as `nice -n 10 ninja -j1 stdlib/swift-stdlib-ohos-aarch64`.
Current build-tree experiments include IR-to-OHOS-clang object handoff for
`Swift.o` and `SwiftOnoneSupport.o`, plus generated `-fPIC` propagation for
OHOS/aarch64 C/C++ runtime objects. As of 2026-07-30 19:25 CST the run had
reached `[132/1086]` with no new failure marker and healthy memory headroom.

## 2026-07-30 Late Evening Stdlib/Private Runtime Update

The later stdlib resume confirmed that the `SwiftGlibc` search path is fixed
and shifted the active frontier into private stdlib/runtime libraries. Three
private-library object targets repeated the same OHOS backend pattern:

- `SwiftPrivate.o` direct object emission failed, but corrected `-emit-ir`
  produced non-empty IR. `opt -verify`, `opt -S -strip-debug`, and the OHOS
  clang wrapper produced a valid aarch64 relocatable object, and the single
  Ninja edge was patched to copy it.
- `SwiftPrivateLibcExtras.o` repeated the same pattern and was attached with a
  single copy edge after the stripped IR compiled through OHOS clang.
- `SwiftPrivateThreadExtras.o` first exposed an OHOS `pthread_t` import
  mismatch: upstream's Linux branch assumes `pthread_t()` is
  default-constructible, but the tested OHOS sysroot imports it as an opaque
  pointer and `pthread_create` expects a pointer to optional `pthread_t`. A
  remote source experiment excludes `SWIFT_STDLIB_OS_OHOS` from that Linux
  branch, and generated OHOS Swift commands were patched to pass
  `-D SWIFT_STDLIB_OS_OHOS`. After that source fix, the target advanced to the
  same object-emission trap and a watchdog-wrapped IR probe produced an
  object-ready `SwiftPrivateThreadExtras.strip-clang.o`. After SSH recovered,
  the single-edge copy rule was installed and the target became a 64 KiB arm64
  ELF relocatable object.

Representative evidence:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-SwiftPrivate-ll-opt-clang-20260730-221949.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-SwiftPrivateLibcExtras-ll-opt-clang-20260730-222354.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-SwiftPrivateThreadExtras-20260730-223719.status
```

Direct SSH to `10.62.230.12:2222` reset during key exchange once in this
window, then recovered. No `unxip` package CI was run in that window.

## 2026-07-30 Final Stdlib/Runtime Update

The constrained final resume completed the full OHOS stdlib/runtime target:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-stdlib-ohos-aarch64-full-j1-20260730-230325.log
END=2026-07-30 23:04:01 CST rc=0
```

Follow-up true-device probes confirmed the requested frontiers:

- the generated `build.ninja` now carries
  `-fmodule-map-file=.../lib/swift/ohos/aarch64/glibc.modulemap`;
- a minimal `import Glibc` typecheck returned `typecheck_rc=0`;
- `swift --version` and `swiftc --version` report Swift 6.0.3 with target
  `aarch64-unknown-linux-ohos`;
- the OHOS/aarch64 stdlib output directory contains `libswiftCore.so`,
  `libswiftGlibc.so`, private stdlib libraries, unittest libraries,
  `_Builtin_float`, and target `.swiftmodule` files for `Swift`, `Glibc`,
  `SwiftPrivate*`, `SwiftOnoneSupport`, `_Builtin_float`, and unittest modules.

The produced `libswiftCore.so` depends on `libc++_shared.so` and `libc.so`;
`libswiftGlibc.so` depends on `libswiftSwiftOnoneSupport.so`,
`libswiftCore.so`, `libc++_shared.so`, and `libc.so`. No Linux/glibc sonames
were observed in these spot checks.

This upgrades the evidence from "stdlib graph pending" to "remote experimental
stdlib/runtime graph passed". It remains experimental because the current state
uses build-tree patches/workarounds for raw PCM ClangImporter behavior,
IR-to-OHOS-clang object handoff, generated `-fPIC` propagation, OHOS Glibc
modulemap/header compatibility, and OHOS pthread import shape. Those need
source-level patches and repeatable packaging before SwiftPM packages such as
`unxip` should be retried.

## 2026-07-30 User Program Runtime Probe

After the stdlib/runtime pass, two signed user-program smokes executed on the
true device through a manual IR-to-OHOS-clang handoff:

- A minimal `print` program verified and stripped the emitted LLVM IR, compiled
  it with the OHOS clang wrapper, linked with `swiftrt.o` and the staged Swift
  runtime libraries, signed the binary, and printed `hello-ohos-swift` with
  `run_rc=0`.
- A minimal `import Glibc` program repeated the path and printed
  `hello-ohos-glibc` with `run_rc=0`. Autolink extracted
  `-lswiftSwiftOnoneSupport`, `-lswiftCore`, and `-lswiftGlibc`.

The same probes also define the unresolved compiler boundary. The frontend
still exits with signal 5 after producing IR (`emit_ir_rc=133` in the Glibc
probe), so the current success proves runtime/link viability but does not yet
prove ordinary `swiftc` object emission. SwiftPM is also absent from the build:
`swift-package` and `swift-build` subcommands both report `No such file or
directory`. LLDB is not a usable crash-capture path yet because `liblldb.so`
relocation fails on missing Python 3.11 symbols.

## 2026-07-31 TargetMachine Lifetime Boundary

Follow-up true-device instrumentation resolved the frontend signal 5 root cause
more precisely. Minimal Swift `typecheck`, `emit-silgen`, and `emit-sil`
returned rc 0. `emit-irgen` and `emit-ir` wrote complete IR but trapped during
cleanup. Markers showed `IRGenRequest::evaluate`, `IRGenModule::finalize`,
`embedBitcode`, `IRGenModule::intoGeneratedModule`, `IRGenModule` destruction,
`performLLVM`, and `generateCode` all completed. The trap occurred when
`GeneratedModule` destroyed its owned LLVM `TargetMachine`.

An experimental OHOS-host workaround that releases the `GeneratedModule`
`TargetMachine` instead of destroying it let the frontend return successfully:
minimal `emit-irgen` rc 0, minimal `emit-ir` rc 0, minimal `frontend -c` rc 0
with an arm64 ELF relocatable object, and `import Glibc` `emit-ir` rc 0 with
the OHOS `glibc.modulemap`. This turns the earlier manual IR handoff into a
more direct frontend object/IR path, but it is still not clean enough for a
reusable toolchain because the remote tree contains probe logging and the
workaround leaks the target machine.

The next boundary is the complete driver/link layer. With writable `TMPDIR`,
the legacy driver reaches frontend compilation but still fails later. Its dry
run uses `/storage/Users/currentUser/usr/local/bin/clang -fuse-ld=gold`, while
the proven manual runtime path uses the OHOS clang wrapper and lld-shaped link
settings. SwiftPM remains absent.

## 2026-07-31 Legacy Driver Link Breakthrough

The next follow-up turned the previous frontend-only success into a direct
legacy-driver smoke. After cleaning the `FrontendTool.cpp` probe prints, the
OHOS `TargetMachine` lifetime workaround rebuilt successfully:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swift-frontend-clean-targetmachine-release-20260731-005549.log
[17/17] Linking CXX executable bin/swift-frontend
rc=0
```

Minimal frontend probes then returned rc 0 for `emit-ir`, `frontend -c`, and
`import Glibc` `emit-ir` with the generated OHOS `glibc.modulemap`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-clean-frontend-20260731-010143-emit-ir.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-clean-frontend-20260731-010143-c.log
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-clean-frontend-20260731-010143-glibc-emit-ir.log
RC emit_ir=0 frontend_c=0 glibc_emit_ir=0
```

The full `swiftc` driver was then split into its generated stages. Frontend
compilation and `swift-autolink-extract` returned rc 0. The remaining failure
was the final link command because the legacy driver directly execed the
`/storage/Users/currentUser/usr/local/bin/clang` shell wrapper, which OHOS/HMDFS
rejects with rc 126. Directly using the real `clang-15` ELF with `lld` and
`-Wl,--code-sign` linked and ran the same Swift object.

A small OHOS-specific driver experiment now:

- returns `lld` from `GenericUnix::getDefaultLinker()` for
  `llvm::Triple::isOHOSFamily()`;
- adds `-Wl,--code-sign` to OHOS dynamic link jobs;
- selects executable `clang-15` as the OHOS linker driver instead of the shell
  `clang` wrapper.

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

This is the first evidence here that the experimental OHOS-hosted Swift 6.0.3
`swiftc` legacy driver can compile, autolink, link/sign, and run a Swift user
program directly. Remaining boundaries are `swift-driver-new` absence,
SwiftPM absence (`swift-package`/`swift-build`), historical probe logging in
several source files, and the need to turn the current remote source experiments
into a minimal, reviewable patch series.

## 2026-07-31 Swift Driver Dependency Chain Probe

The next step attempted to move from the deprecated legacy driver to the missing
`swift-driver-new` layer. The true-device source tree contains `repos/swift-driver`
and `repos/swiftpm`, but the current compiler build graph does not include
`swift-driver`, `swift-package`, or `swift-build` targets.

A separate `swift-driver` CMake probe configured with the experimental OHOS
`swiftc`. A direct build first failed on missing `TSCBasic`, proving that the
driver dependency chain was not staged. The pinned dependencies from
`repos/swift-driver/Package.resolved` were fetched on the Windows host and
transferred to the true device because the true device lacks `git`/`curl`:

```text
swift-argument-parser: 8f4d2753f0e4778c76d5f05ad16c74f707390531
swift-llbuild: a3b8d34be319f1b3ba8de53c434386419dec1f4f
swift-tools-support-core: 3b13e439a341bbbfe0f710c7d1be37221745ef1a
Yams: 0d9ee7ea8c4ebd4a489ad7a73d5c6cad55d6fed3
swift-system: 025bcb1165deab2e20d4eaba79967ce73013f496
```

That surfaced the next platform layers:

- CMake/llbuild must use real executable `clang-15` for CXX, not the
  `/storage/.../clang++` shell wrapper. `CMAKE_CXX_COMPILER_ARG1=--driver-mode=g++`
  gets CXX configure past this boundary.
- `llbuild` requires SQLite3. A temporary sqlite3 3.49.1 staging build now
  exists under `/storage/Users/currentUser/swift-mainline-ohos-src/stage/sqlite3-3.49.1-ohos`.
- TSC requires `SwiftSystemConfig.cmake`, so SwiftSystem must be built first.
- SwiftSystem needs an OHOS `O_ACCMODE` shim. OHOS `fcntl.h` defines
  `O_ACCMODE` through `O_SEARCH`, which ClangImporter cannot import; the
  experiment uses `03 | O_PATH`, and `O_PATH` imports successfully.

SwiftSystem then hit a compiler backend boundary. `SystemPackage` direct object
emission crashes with signal 11, even after configuring CMake with
`CMAKE_Swift_COMPILATION_MODE=wholemodule` and `CMAKE_Swift_NUM_THREADS=1`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-install-swift-system-ohos-wmo-20260731-015452.log
swiftc -frontend -c -primary-file .../Sources/System/Errno.swift ...
Signal 11
```

The same frontend command changed from `-c` to `-emit-ir` succeeds:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-swiftsystem-errno-emit-ir-20260731-015452.log
RC=0
OUT_SIZE=292096
```

So the new-driver route has advanced from missing dependencies into an
object-emission/IR-handoff boundary inside SwiftSystem. The probable next step
is to produce SwiftSystem objects through the same IR-to-OHOS-clang path used
for stdlib objects, install SwiftSystem as a CMake package, then resume TSC,
LLBuild, and SwiftDriver.

## 2026-07-31 FoundationCollections Handoff Probe

After SwiftSystem and libdispatch were staged far enough for the Foundation
probe, `swift-corelibs-foundation` configured successfully with XML and
Networking disabled:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/configure-foundation-ohos-probe1-20260731-033718.log
CONFIG_RC=0
```

The first Foundation build target still failed at direct
`_FoundationCollections` object emission with signal 11:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-foundation-ohos-probe1-j1-20260731-033842.log
```

A primary-file IR handoff probe then emitted the `_FoundationCollections`
module once and processed bounded primary source sets through
`swiftc -frontend -emit-ir`, `opt -verify -disable-output`, `opt -S
-strip-debug`, and the OHOS clang wrapper. The first two bounded runs passed:

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

This is the third major Swift package layer where OHOS-host direct object
emission is unreliable while IR handoff to the OHOS LLVM fork remains viable.
The full `_FoundationCollections` module was then audited and archived:

```text
TOTAL=155
EXISTS_NONZERO=155
MODULE_OK=1
OUT_SIZE=4267042
```

The true-device build tree needed a temporary, target-specific Ninja rule
override so `_FoundationCollections` would not rerun the original direct
`swiftc -c` edge. The override affected only
`Swift_COMPILER___FoundationCollections_unscanned_Release` and
`Swift_STATIC_LIBRARY_LINKER___FoundationCollections_Release`; the original
rules were backed up in the build directory. After the override,
`ninja -n _FoundationCollections` reported no work.

Resuming `Foundation` compiled `_FoundationCShims` and Foundation ICU C/C++
sources, then stopped at `FoundationEssentials` semantic analysis rather than a
backend crash. The failure cluster is:

```text
secure_getenv missing from imported OHOS libc surface
FTS/FTSENT/fts_* missing from imported OHOS libc surface
Regex/RegexComponent unavailable
macro declarations rejected as unsupported
```

Small probes confirmed that the current OHOS stdlib staging cannot import
`_Concurrency` or `_StringProcessing`, and `Regex` is absent:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundation-frontend-features-20260731-145819.log
REGEX_RC=1
MACRO_RC=1
```

The Swift source tree has `stdlib/public/Concurrency`, `RegexParser`,
`StringProcessing`, and `RegexBuilder`, but the current OHOS build graph does
not include their targets. The next mainline task is to enable/stage those
stdlib feature modules for OHOS, including `SWIFT_MODULE_DEPENDS_OHOS Glibc`
mapping where appropriate and a source path for the external string-processing
library, before retrying FoundationEssentials and returning to `swift-driver`
and SwiftPM.

## 2026-07-31 Stdlib Feature Module Staging

The external string-processing source required by Swift 6.0.3 was pinned to the
official Swift repository tag:

```text
swiftlang/swift-experimental-string-processing
swift-6.0.3-RELEASE
9c50f6da9be4b4a828cec31adbef758a6c3673d6
```

It was staged on the true device under
`/storage/Users/currentUser/swift-mainline-ohos-src/deps/swift-experimental-string-processing-src`
after sha256 verification of the transferred archive. The existing Swift build
tree was reconfigured with:

```text
SWIFT_ENABLE_EXPERIMENTAL_CONCURRENCY=ON
SWIFT_CONCURRENCY_GLOBAL_EXECUTOR=hooked
SWIFT_ENABLE_EXPERIMENTAL_STRING_PROCESSING=ON
SWIFT_PATH_TO_STRING_PROCESSING_SOURCE=/storage/Users/currentUser/swift-mainline-ohos-src/deps/swift-experimental-string-processing-src
```

The reconfigure completed with `CMAKE_RC=0` in
`logs/reconfigure-swift-stdlib-concurrency-stringprocessing-20260731-161744.log`
and produced OHOS Ninja targets for `_Concurrency`, `_RegexParser`,
`_StringProcessing`, and RegexBuilder. The guarded next build is
`nice -n 10 ninja -j1 swift_Concurrency-ohos`, logged at
`logs/build-swift-Concurrency-ohos-j1-20260731-161949.log`. The first observed
phase is a single-job Swift compiler C++ incremental rebuild caused by enabling
the experimental stdlib flags; the task is being monitored before the Regex and
FoundationEssentials retries.

The first guarded run rebuilt the affected Swift compiler C++ libraries and
linked a new `bin/swift-frontend`, then stopped when the generated stdlib edge
tried to rebuild `Swift.o` directly:

```text
[910/1041] Linking CXX executable bin/swift-frontend
[913/1041] Compiling .../stdlib/public/core/OHOS/aarch64/Swift.o
Running pass 'AArch64 Assembly Printer'
error: unable to execute command: Segmentation fault
error: compile command failed due to signal 11
NINJA_RC=1
```

This is not a new source-level concurrency failure. It means the previous
Swift core IR handoff must be repeated with the newly enabled
`SWIFT_ENABLE_EXPERIMENTAL_CONCURRENCY` and
`SWIFT_ENABLE_EXPERIMENTAL_STRING_PROCESSING` flags before `_Concurrency` and
the Regex modules can proceed. Monitoring after the failed edge showed no
remaining Swift/ninja process from this task, with about 14.5 GiB
MemAvailable and 49.4 GiB SwapFree. No further Swift target or unxip CI was
started.

## 2026-08-01 FoundationEssentials Bootstrap Link And Runtime Probe

The OHOS-native Swift path progressed through the missing stdlib feature-module
boundary and into `FoundationEssentials`. A full primary-file IR handoff
completed on the true device:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-primary-handoff-20260801-005338.log
FE_HANDOFF_REUSE_MODULE=1
clang_ok=182/182
status=0
real_errors=0
```

The handoff reused the emitted `FoundationEssentials.swiftmodule`, emitted IR
for each primary source, verified/stripped it with `opt`, and compiled the IR
to OHOS/aarch64 relocatable objects with the OHOS clang wrapper. Audit against
CMake's output-file-map reported 182/182 present, nonzero objects and a
3,987,972-byte module file.

The first manual shared-library link intentionally skipped the original Ninja
WMO edge and exposed duplicate symbols from the `_FoundationCollections`
IR-handoff archive:

```text
ld.lld: error: duplicate symbol: $s22_FoundationCollections9BigStringVSlAAMc
ld.lld: error: duplicate symbol: $s22_FoundationCollections9BigStringVSlAAWP
```

An `llvm-nm` scan found 176 duplicate symbols among 5,573 defined archive
symbols, so this is a broad handoff/archive artifact rather than a single
source typo. For bootstrap proof only, the final link was retried with
`-Xlinker --allow-multiple-definition`; it produced
`lib/libFoundationEssentials.so` with size 13,426,176 bytes.

`llvm-readobj` showed an OHOS/aarch64 shared object with these dynamic
dependencies:

```text
NEEDED: libswiftSwiftOnoneSupport.so
NEEDED: libswiftCore.so
NEEDED: libswift_Concurrency.so
NEEDED: libswift_StringProcessing.so
NEEDED: libswiftGlibc.so
NEEDED: libc.so
RUNPATH: /storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos::::::::
```

A minimal executable importing `FoundationEssentials` compiled and ran on the
true device:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-exe-20260801-022741.log
compile_rc=0
run_rc=0
stdout: 0
```

Remaining mainline work is to replace the muldefs bootstrap with correct
weak/linkonce symbol handling for IR-handoff archives, remove the temporary
`OHOS_BOOTSTRAP_NO_MACROS` predicate guard or implement macro support, clean
the malformed Swift/CMake RUNPATH, and convert the handoff/link sequence into
repeatable build rules before returning to SwiftPM and the `unxip` validation
package.

A follow-up in the same window found only two strong duplicate symbols in the
`_FoundationCollections` archive, both BigString conformance artifacts. A
weakened archive copy was produced with `llvm-objcopy --weaken-symbol` for
those two names. Linking `FoundationEssentials` against the weakened archive
then succeeded without `--allow-multiple-definition`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/run-foundationessentials-link-weaken-fc-validname-20260801-023624.log
link_rc=0
```

The standard build-tree artifact names were switched to the weakened archive
and weakened-link shared object, and the standard
`lib/libFoundationEssentials.so` path was revalidated:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-standard-exe-20260801-023951.log
compile_rc=0
run_rc=0
stdout: 0
```

This narrows the mainline archive issue to repeatable detection and weakening
of strong duplicate symbols emitted by primary-file IR handoff.

The malformed `::::::::` RUNPATH was separately traced to an explicit empty
rpath fragment in the final link command. Relinking without that fragment,
while using the weakened archive, produced a clean `RUNPATH` containing only
the Swift OHOS runtime directory:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/run-foundationessentials-link-clean-rpath-20260801-024228.log
RUNPATH: /storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/lib/swift/ohos
```

The clean-rpath shared object passed the same minimal executable probe and was
installed as the standard `lib/libFoundationEssentials.so` build-tree artifact.

The `_FoundationCollections` archive helper in the true-device probe area was
then updated to run the strong-duplicate detection and `llvm-objcopy`
weakening automatically after archiving. The regression run reported:

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

The FoundationEssentials handoff-to-link sequence was also captured in
`tmp/link_foundationessentials_from_handoff.py`. The helper reads the Ninja
commands, skips the original dirty WMO edge, runs C shims and the updated
archive helper, removes the empty rpath fragment, links the shared object, and
installs the standard clean artifact:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/link-foundationessentials-from-handoff-20260801-024854.log
COMMANDS=9
SKIP_ORIGINAL_WMO=1
END rc=0
```

The helper-installed standard artifact was revalidated by a true-device
executable importing FoundationEssentials:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-after-helper-exe-20260801-024935.log
compile_rc=0
run_rc=0
stdout: 0
```

The handoff result was then integrated into the generated Foundation Ninja
build tree for `FoundationEssentials`. The remote build tree was backed up and
patched only for the target-specific WMO compile edge and empty-rpath link
variable:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/build/foundation-ohos-probe1/CMakeFiles/rules.ninja.pre-fe-noop-20260801-030146.bak
/storage/Users/currentUser/swift-mainline-ohos-src/build/foundation-ohos-probe1/build.ninja.pre-fe-noop-20260801-030146.bak
```

`nice -n 10 ninja -j1 FoundationEssentials` completed with rc 0 in:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/ninja-foundationessentials-integrated-20260801-030348.log
```

`ninja -n FoundationEssentials` now reports `ninja: no work to do`, proving
that Ninja has accepted the audited handoff objects and clean final link
instead of trying to rerun the unstable 182-source direct WMO object emission.
The resulting `libFoundationEssentials.so` has a clean RUNPATH to the Swift
OHOS runtime directory and the expected NEEDED set:

```text
libswiftSwiftOnoneSupport.so
libswiftCore.so
libswift_Concurrency.so
libswift_StringProcessing.so
libswiftGlibc.so
libc.so
```

A fresh post-integration executable probe also passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationessentials-after-ninja-exe-20260801-030631.log
compile_rc=0
run_rc=0
```

The operational lesson from this step is that all Swift compile/link probes on
this OHOS device must set `TMPDIR` to a writable path under the Swift probe
root; otherwise the Swift driver fails with read-only temporary-file errors.
The guarded Ninja integration was monitored in:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/monitor-foundationessentials-integrated-20260801-030348.log
```

At the start of that run, MemAvailable was about 13.26 GiB and SwapFree about
48.93 GiB.

## Related Knowledge

- E105 and E172 document the same class of Linux toolchain/runtime boundary for
  older Rust failures.
- E180 documents the resolved Rust case where a new HNP toolchain provides an
  OHOS-capable Rust target. Swift currently lacks the equivalent resolved
  toolchain evidence in this workspace.

## 2026-08-01 FoundationInternationalization Update

`FoundationInternationalization` advanced after the integrated
`FoundationEssentials` handoff. Direct generated WMO object emission failed in
`build-foundationinternationalization-j1-20260801-031425.log` with Swift
frontend signal 11, matching the direct object-emission crash class already
seen in Swift stdlib and Foundation modules on OHOS/aarch64.

The primary-file IR handoff path succeeded:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe_foundationinternationalization_primary_handoff.py
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundationinternationalization-primary-handoff-20260801-032408.log
60/60 primary files
60 object files
rc=0
```

The generated Foundation Ninja tree was then patched only around the
`FoundationInternationalization` WMO edge and link variables. The guarded run in
`ninja-foundationinternationalization-integrated-20260801-035129.log` completed
with `BUILD_RC=0`, and `ninja -n FoundationInternationalization` reported no
work to do.

The current boundary is no longer Swift compilation for that target. A minimal
`import FoundationInternationalization` executable compiles, but runtime fails
with `run_rc=127` in
`probe-foundationinternationalization-exe-20260801-035444.log`. The ICU support
library exports sampled symbols such as `u_vformatMessage`, `ucal_getNow`,
`udat_applyPattern`, `uloc_getLanguage`, `ures_open`, and `ucol_open`, while
the loader still reports `Error loading shared library lib_FoundationICU.so`
and unresolved ICU symbols.

Dynamic audit narrowed the next investigation to OHOS loader policy rather
than missing ICU codegen:

```text
lib_FoundationICU.so RUNPATH: :::::::
lib_FoundationICU.so NEEDED: libc++_shared.so, libc.so
lib_FoundationICU.so has no observed .codesign section
libFoundationInternationalization.so has .codesign and a Foundation lib RUNPATH
```

Next steps are to run small loader probes for `lib_FoundationICU.so`, remove or
relink the dirty empty RUNPATH if necessary, sign or re-sign the ICU artifact if
OHOS requires it, and confirm `libc++_shared.so` resolution before attempting a
broader `Foundation` target, SwiftPM, or `unxip` validation.

## 2026-08-01 Foundation Main Module Update

The next true-device resume advanced past the broader `Foundation` runtime
boundary. `libFoundation.so` initially failed to load because it referenced
`posix_spawn_file_actions_addchdir`, which is not exported by the tested OHOS
libc. The generated C flags define `__OHOS__` and `__MUSL__`, while the
upstream CoreFoundation conditional only checked lower-case `__musl__`, so OHOS
fell through to the standard POSIX.1-2024 call.

An OHOS-specific probe patch in
`swift-corelibs-foundation/Sources/CoreFoundation/CFPlatform.c` makes
`_CFPosixSpawnFileActionsChdir` return `ENOSYS` under `defined(__OHOS__)`.
Rebuilding with `TMPDIR=/storage/Users/currentUser/swift-mainline-ohos-src/tmp`
and `nice -n 10 ninja -j4 Foundation` completed successfully:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-Foundation-after-ohos-addchdir-j4-20260801-1215.log
RC=0
```

After re-signing the Foundation and dispatch runtime shared libraries, a fresh
minimal executable importing Foundation compiled and ran on the true device:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/foundation-smoke-compile-20260801-121709.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/run-foundation-smoke-after-ohos-addchdir-20260801-1218.console.log
COMPILE_RC=0
RUN_RC=0
stdout: foundation-smoke 0
```

Monitoring stayed safe during this stage, with about 14 GiB `MemAvailable` and
49 GiB `SwapFree` at smoke start. The next mainline target is no longer
Foundation startup itself; it is making the temporary OHOS CoreFoundation
patch, IR-handoff rules, runtime signing, and new-driver/SwiftPM path
repeatable enough for package validation.

## 2026-08-01 Swift New-Driver Update

The OHOS-native Swift route has now advanced from runtime-library smoke tests
to a runnable `swift-driver` prototype. The generated CMake build for
`SwiftDriver`, `SwiftDriverExecution`, and the final `swift-driver` executable
hit the same direct Swift object-emission crash class as prior stdlib and
Foundation modules. The successful path was the established primary-file IR
handoff through the OHOS LLVM fork:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftdriver-handoff-20260801-151610.log
SwiftDriver: 110/110 primary files, link_rc=0, lib_size=7929216

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftdriverexecution-handoff-20260801-161556.log
SwiftDriverExecution: 3/3 primary files, link_rc=0, lib_size=339328

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swift-driver-exe-handoff-20260801-164004.log
swift-driver executable: emit_ir_rc=0, objectize_rc=0, link_rc=0, exe_size=89600
```

The executable path also found a terminfo dependency in `libllbuildSwift.so`.
The existing device library
`/storage/Users/currentUser/usr/local/lib/libtinfo.so.6` provides
`setupterm`, `tigetnum`, `set_curterm`, and `del_curterm`; the executable
handoff links it and adds the user-local library directory to RUNPATH.

Runtime validation now passes when invoked through recognized argv0 names. The
probe uses copied `swiftc` and `swift` binaries because symlink creation is
denied on the tested filesystem:

```text
TMPDIR=/storage/Users/currentUser/swift-mainline-ohos-src/tmp
PATH=/storage/Users/currentUser/swift-mainline-ohos-src/build/swift-manual-ohos-linuxsys2/bin:$PATH

build/swift-driver-ohos-probe5/probe-bin/swiftc -version
Swift version 6.0.3 (swift-6.0.3-RELEASE)
Target: aarch64-unknown-linux-ohos

build/swift-driver-ohos-probe5/probe-bin/swiftc -print-target-info
target.triple = aarch64-unknown-linux-ohos
```

Remaining boundaries are to make the IR handoff and Ninja integration
reviewable, remove probe logging, settle a real install strategy for
`swiftc`/`swift` argv0 behavior, stage `swift-help`, then build SwiftPM
subcommands before using `unxip` as the package-level validation.

## 2026-08-01 Swift New-Driver Linker Selection Update

The new-driver probe advanced from metadata commands to a plain compile/link/run
path. A narrow OHOS experiment in
`SwiftDriver/Jobs/GenericUnixToolchain+LinkerSupport.swift` now handles the
target triple by selecting the real `clang-15` executable, adding the staged
OHOS sysroot when no SDK is supplied, defaulting to `lld`, and passing
`-Wl,--code-sign`.

The validating rebuild completed all probe layers:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftdriver-handoff-20260801-181706.log
SwiftDriver: 110/110 primary files, link_rc=0

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftdriverexecution-handoff-20260801-191242.log
SwiftDriverExecution: 3/3 primary files, link_rc=0

/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swift-driver-exe-handoff-20260801-191435.log
swift-driver executable: emit_ir_rc=0, objectize_rc=0, link_rc=0
```

Validation used a fresh copied argv0 probe directory:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/probe-bin-linkerpatch2-20260801-1916
```

With `SWIFT_DRIVER_CLANG_EXEC` unset and no explicit `-sdk`/`-use-ld` on the
compile command, `swiftc -version`, `swiftc -print-target-info`, and
`swiftc -help` all returned rc 0. The `-###` trace for a minimal hello program
showed `/storage/Users/currentUser/usr/local/bin/clang-15`, `-fuse-ld=lld`,
`--sysroot /storage/Users/currentUser/usr/local/sysroot`, and
`-Wl,--code-sign`. The resulting executable printed
`hello-new-driver-ohos` with `run_rc=0`.

The next boundary is SwiftPM command availability, not single-file new-driver
linking. Build or stage `swift-package`/`swift-build` before using `unxip` as a
package-level validation case.

## Observation: SwiftASN1 PEM API depends on Foundation importability

During the SwiftPM dependency-chain probe, `swift-certificates` `X509`
initially failed at module emission because `PEMDocument`,
`PEMRepresentable`, `PEMParseable`, and `PEMSerializable` were not visible from
the rebuilt SwiftASN1 module. Inspection of upstream SwiftASN1 showed that
`Sources/SwiftASN1/Basic ASN1 Types/PEMDocument.swift` is compiled only when
`canImport(Foundation)` or `canImport(FoundationEssentials)` is true.

The initial OHOS-native SwiftASN1 handoff had built successfully without those
symbols because it did not pass the staged Foundation Swift module path and
Foundation client C modulemaps. Rebuilding SwiftASN1 with those search paths
made `PEMDocument.swift` participate in code generation and restored the PEM
API:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-swiftasn1-handoff-20260801-2143-foundation.log
PEMDocument.swift: emit_ir_rc=0, objectize_rc=0
SwiftASN1: link_rc=0

/storage/Users/currentUser/swift-mainline-ohos-src/logs/asn1-pem-smoke-20260801-215352.log
PEM API typecheck rc=0
```

The subsequent `X509` probe then passed `emit-module`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-cert-X509-handoff-20260801-2155-pemfix.log
MODULE=X509
total_sources=99
emit_module_rc=0
```

This is an important repeatability note for Path B/C: Swift package dependency
probes must preserve both Swift module search paths and the Foundation
client-facing C modulemaps, otherwise conditional APIs can silently disappear
from an otherwise successful dependency build.

## 2026-08-02 SwiftPM entry point update

The OHOS-native route now has runnable SwiftPM entry points for a minimal
package smoke. The SwiftPM build tree provides:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/build/swiftpm-ohos-probe1/bin/swift-package
/storage/Users/currentUser/swift-mainline-ohos-src/build/swiftpm-ohos-probe1/bin/swift-build
```

Both report:

```text
Swift Package Manager - Swift 6.0.3
```

Two important build-tree fixes were validated:

1. `PackageDescription` can be staged beside the SwiftPM executables in
   `swiftpm-ohos-probe1/bin`. After copying `PackageDescription.swiftmodule`,
   `.swiftdoc`, `.swiftsourceinfo`, and `libPackageDescription.so`, direct
   `$SPM/bin/swift-package dump-package` works and no longer needs the
   temporary `swiftpm-bin-manifestapi-copy-20260802-1045` executable shim.
2. `libllbuildSwift.so` must explicitly depend on the terminfo provider. The
   successful link-only relink used `-l:libtinfo.so.6`; after that,
   `llvm-objdump -p libllbuildSwift.so` reports `NEEDED libtinfo.so.6`, and
   `swift-build --version` runs without `LD_PRELOAD=libtinfo.so.6`.

The validating relink log is:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/relink-llbuildswift-tinfo-linkonly-20260802-112804.log
```

Minimal package validation then passed in two forms:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/swift-build-smoke-no-tinfo-preload-20260802-112915
Build complete! (21.32s)
Hello, world!
hello_rc=0

/storage/Users/currentUser/swift-mainline-ohos-src/tmp/swift-build-smoke-spmbin-20260802-113522
Build complete! (21.13s)
Hello, world!
hello_rc=0
```

The produced executable uses the OHOS musl interpreter
`/lib/ld-musl-aarch64.so.1`, has RUNPATH to the staged Swift OHOS runtime plus
`$ORIGIN`, and needs `libswiftSwiftOnoneSupport.so`, `libswiftCore.so`,
`libswift_Concurrency.so`, `libswift_StringProcessing.so`, and `libc.so`.

Remaining boundaries are still significant: the package smoke uses a
diagnostic libdispatch/concurrency hook, a diagnostic `swiftc -modulewrap`
shim for the current modulewrap crash, manual SDK/resource-dir/Glibc modulemap
flags, and SwiftCrypto diagnostic workarounds. This means the observation has
advanced from "Swift is absent" to "OHOS-native SwiftPM can build and run a
minimal package under diagnostic supports", but `unxip` should remain a later
validation target until these supports are formalized.

## 2026-08-02 dispatch-backed SwiftPM update

The follow-up removed the previous concurrency preload from the minimal SwiftPM
path. `libswift_Concurrency.so` was rebuilt with
`SWIFT_CONCURRENCY_USES_DISPATCH=1`, staged OHOS libdispatch link paths, and an
IR-to-llc handoff for `_Concurrency.o` after direct Swift backend codegen
continued to crash on the AArch64/OHOS debug-info path.

Evidence:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-concurrency-dispatch-pic-uses-ninja-20260802-124248.log
NINJA_RC=0
```

The resulting runtime exports `swift_task_enqueueOnDispatchQueue`, contains
`DispatchQueueShim` witness-table symbols, and needs `libdispatch.so` plus
`libBlocksRuntime.so`.

A no-preload SwiftPM smoke then passed the old dispatch/runtime blocker and
exposed missing manifest `-sdk` propagation instead of a missing sysroot. A
self-signed native ELF `swiftc` wrapper proved the narrow SDK/resource-dir/Glibc
modulemap fix:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/swiftc-modulewrap-sdkelf-20260802-1312/swiftc
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-dump-sdkelf-20260802-1318.log
RC=0
```

With `--disable-index-store`, SwiftPM built and ran a debug package:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-build-sdkelf-noindex-20260802-1328.log
Build complete! (23.40s)

/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-run-audit-sdkelf-20260802-1333.log
hello swiftpm ohos
```

An async smoke using `async main` and `Task.yield()` also passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-async-build-run-sdkelf-20260802-1400.log
Build complete! (28.52s)
async swiftpm ohos
```

Remaining boundaries are source/CMake formalization of dispatch and IR handoff,
real SwiftPM/toolchain sysroot propagation instead of the SDK ELF wrapper,
index-store handling for OHOS, replacement of the modulewrap diagnostic shim,
and investigation of the release/`-O` Swift frontend crash.

## 2026-08-02 SwiftPM index-store fix probe

A follow-up narrowed the SwiftPM default-index-store failure to Swift
ClangImporter argument propagation. The old failure passed
`-index-store-path` through to the OHOS clang driver, which treated it as an
unknown argument and produced an unexpected second clang job. A narrow
experimental frontend patch filters that option from ClangImporter driver
arguments for `aarch64-unknown-linux-ohos`, then rebuilt `bin/swift-frontend`
and `bin/swiftc`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/rebuild-swiftfrontend-indexstore-20260802-133739.log
RC=0
```

Default-index-store SwiftPM debug validation now passes with the known manual
OHOS SDK/resource-dir/Glibc modulemap flags:

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

The pure `swift-build --triple` path still fails the final link without the
manual SDK propagation, so sysroot/resource-dir/modulemap handling remains a
separate toolchain integration boundary. During the probe, dispatch runtime
libraries also had to be copied into the Swift OHOS runtime directory so
manifest execution could resolve `libswiftDispatch.so`, `libdispatch.so`, and
`libBlocksRuntime.so` through the existing RUNPATH.

## 2026-08-02 SwiftPM release IR handoff

Release-mode SwiftPM was split to isolate the failing stage. The direct
frontend matrix in
`/storage/Users/currentUser/swift-mainline-ohos-src/logs/release-frontend-variants-20260802-141443.log`
shows that `-O -emit-sil` passes, `-O -emit-ir` returns signal 5/RC 133 while
writing non-empty IR, and direct `-O` object emission returns signal 11/RC 139
with a zero-byte object. A manual IR handoff then compiled the release IR with
the OHOS LLVM fork's `clang-15`, used the diagnostic modulewrap shim for the
module object, linked successfully, and ran the executable on device:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/release-irhandoff-link-20260802-141640.log
CLANG_RC=0
LINK_RC=0
RUN_RC=0
stdout: release xswiftc ohos
```

The current interpretation is that release mode is feasible but not yet
formalized. The remaining reviewable work is to replace the direct backend
object crash with either a source fix or a repeatable IR-to-object rule, and to
replace the diagnostic modulewrap shim with source-level behavior.

## 2026-08-02 SwiftPM default SDK propagation

The SwiftPM debug smoke no longer depends on the earlier signed SDK ELF wrapper
for basic sysroot propagation. A narrow SwiftDriver experiment was rebuilt on
the true device:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/repos/swift-driver/Sources/SwiftDriver/Driver/Driver.swift
/storage/Users/currentUser/swift-mainline-ohos-src/repos/swift-driver/Sources/SwiftDriver/Toolchains/GenericUnixToolchain.swift
/storage/Users/currentUser/swift-mainline-ohos-src/logs/build-swift-driver-defaultsdk-j1-20260802-1506.log
NINJA_RC=0
link_rc=0
```

For `linux-ohos`, the driver now obtains a default SDK from
`OHOS_SDKROOT`, `OHOS_SYSROOT`, or `SDKROOT`. Fresh SwiftPM debug packages then
passed through `$MAN/bin/swift build` with `OHOS_SDKROOT` set and without
manual `-Xswiftc -sdk` flags:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-default-defaultsdk-swiftbuild-20260802-164449.log
Build complete! (84.22s)
RUN_RC=0
stdout: default sdk swift build ohos

/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-glibc-defaultsdk-swiftbuild-20260802-165044.log
Build complete! (112.40s)
RUN_RC=0
stdout: glibc default sdk pid 46298
```

The validating logs show Swift frontend commands receiving
`-sdk /storage/Users/currentUser/usr/local/sysroot`, ClangImporter receiving
`--sysroot /storage/Users/currentUser/usr/local/sysroot`, and the Glibc package
linking/depending on `libswiftGlibc.so`. This changes the current
recommendation: after the driver patch is made reviewable, `unxip` can become
the next realistic SwiftPM package validation target, but not before the
modulewrap shim, dispatch/runtime staging, and release IR handoff are also
converted from diagnostics into repeatable toolchain behavior.

## 2026-08-02 SwiftPM release package through IR handoff

The evening release probe validated a complete SwiftPM release package that
imports Glibc through an experimental signed IR-handoff wrapper:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/swift-irhandoff-wrapper-sdkfix-20260802-190734
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-release-irhandoff-sdkfix-20260802-191210.log
Build complete! (112.19s)
BUILD_RC=0
stdout: swiftpm release sdkfix pid 23011
RUN_RC=0
```

The wrapper intercepts optimized Swift frontend `-c`, emits IR, tolerates the
current signal 5/RC 133 when a non-empty IR file has been written, strips debug
metadata, compiles the IR with OHOS `clang-15`, and preserves the signed OHOS
link path. The resulting executable uses `/lib/ld-musl-aarch64.so.1`, has
RUNPATH to the staged Swift OHOS runtime and `$ORIGIN`, and needs
`libswiftSwiftOnoneSupport.so`, `libswiftCore.so`, `libswift_Concurrency.so`,
`libswift_StringProcessing.so`, `libswiftGlibc.so`, and `libc.so`.

This turns release SwiftPM from a speculative blocker into a formalization
problem. The next mainline task is to replace the temporary wrapper with
reviewable Swift frontend/driver/build-system behavior, especially around
optimized object emission, modulewrap, SDK/resource propagation, and required
OHOS code signing.

## 2026-08-02 controlled concurrency and valid-object probe

The next release probe tested whether direct optimized object emission could be
salvaged by accepting valid objects despite a non-zero frontend exit. The
single-file matrix in
`/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-release-direct-debugmeta-20260802-192948.log`
showed two usable non-empty ELF objects (`debug` and `gnone`, both RC 133) and
one zero-byte object (`nodebug`, RC 139). The non-empty objects were linkable
and runnable according to
`/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-release-direct-debugmeta-link-20260802-192948.log`.

That shortcut is not general enough. A full SwiftPM release package using a
valid-object wrapper failed in
`/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-release-validobj-sdkfix-j2-20260802-193829.log`
with `BUILD_RC=1`, `RUN_RC=127`, and `[ohos-validobj] frontend rc=139
valid_elf=0`.

The proven IR handoff path was then rerun with controlled concurrency:
SwiftPM `-j 2` and explicit `-Xswiftc -num-threads -Xswiftc 2`. The full
release Glibc smoke passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-release-irhandoff-sdkfix-j2-t2-20260802-194542.log
Build complete! (112.51s)
BUILD_RC=0
stdout: swiftpm release irhandoff j2 t2 pid 12531
RUN_RC=0
```

This updates the guidance: future probes may raise package/build parallelism
under monitor, but should also cap Swift frontend internal thread counts.
Correctness work should continue on formalizing IR handoff rather than masking
frontend failures after direct object emission.

The controlled concurrency ceiling was then raised to SwiftPM `-j 3` with a
three-library-target plus one executable-target release package. The IR
handoff wrapper produced and linked all four targets:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swiftpm-release-irhandoff-multitarget-j3-t3-20260802-195322.log
Build complete! (166.72s)
BUILD_RC=0
stdout: swiftpm release multitarget j3 t3 138
RUN_RC=0
```

The monitor log remained safe, with the lowest sampled `MemAvailable` around
13.7 GiB and `SwapFree` around 49.5 GiB. The outer SwiftDriver diagnostic
commands can still show `-num-threads 20` while intercepted frontend commands
contain the explicit `-num-threads 3`; that layering needs to be formalized
before higher concurrency becomes a default recommendation.

The same package shape was then run through the normal `swift` front door. A
first attempt failed immediately because `$MAN/bin/swift build` could not find
the `swift-build` subcommand. After adding `$SPM/bin` to `PATH`, the
front-door release build passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/swift-man-build-release-multitarget-pathfix-j3-t3-20260802-200448.log
Build complete! (167.69s)
BUILD_RC=0
stdout: swift frontdoor pathfix release j3 t3 85
RUN_RC=0
```

This shows the remaining integration boundary is now toolchain layout and
runtime-library staging, not the conceptual ability of `swift build` to drive a
release SwiftPM package on OHOS.

## 2026-08-02 unxip Package Probe And FoundationXML Boundary

With SwiftPM release packages passing through the signed IR handoff path,
`unxip/3.3` became the next real validation target. The probe copied the
verified upstream archive to the true device and materialized the upstream
`Sources/libunxip/libunxip.swift -> ../../unxip.swift` symlink as a normal
file because the tested OHOS extraction path rejects that link.

The first unxip release build reached Swift source compilation and failed on
plain Foundation lookup:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/unxip-swiftpm-release-product-j3-t3-20260802-202917.log
error: no such module 'Foundation'
```

Adding the staged Foundation Swift module path moved the build forward. The
current import matrix is:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-unxip-import-matrix-20260802-205729.log
IMPORT_GNUSource=0
IMPORT_getopt=0
IMPORT_zlib=0
IMPORT_Foundation=1
IMPORT_lzma=1
IMPORT_FoundationXML=1
```

`Foundation` itself was then proven usable with its client C module maps:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-foundation-cmodule-paths-20260802-210746.log
RC_COMPILE=0
RC_RUN=0
```

The required additions are the Foundation Swift module directory and the three
client module maps for `_FoundationICU`, `_FoundationCShims`, and
`CoreFoundation`.

`FoundationXML` is not present in the currently validated Foundation staging
directory because that build was intentionally configured with
`FOUNDATION_ENABLE_XML=OFF`. Turning XML on exposed an external header boundary:
the device has a runtime `libxml2.so`, but no default libxml2 development
headers:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/configure-foundation-xml-probe1-20260802-211222.log
Could NOT find LibXml2 (missing: LIBXML2_INCLUDE_DIR)
```

The already published `libxml2/2.15.3` Conan package exists in the true-device
cache and provides the missing header and library paths. A separate XML probe
build configured successfully when those paths were passed explicitly:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/configure-foundation-xml-probe2-20260802-212033.log
Found LibXml2: .../lib/libxml2.so (found version "2.15.3")
CONFIG_RC=0
```

The resulting build graph contains `_CFXMLInterface`,
`FoundationXML.swiftmodule`, and `libFoundationXML.so`. A dry run showed that a
fresh XML build directory would rebuild 574 Foundation/ICU steps, so the next
efficient route is to seed or reuse the already validated Foundation artifacts
and only build the new XML target pieces.

The separate `lzma` import failure is confirmed as missing `lzma.h`. Treat it
as an `xz`/liblzma dependency staging issue, not as Swift toolchain behavior and
not as something to patch inside the unxip recipe.

Operationally, the device was not memory-bound during these probes:
`free=2.6G` was only bare free memory, while `/proc/meminfo` reported roughly
14 GiB `MemAvailable` before the later XML checks and about 12.6 GiB after the
dry run, with about 49 GiB `SwapFree`. After the dry run, both FRP and direct
SSH accepted TCP connections but immediately closed the session. No new Swift
source failure was observed during that connection boundary.

## 2026-08-02 Direct unxip Swift 6 Binary

The next resume completed the efficient FoundationXML path by reusing the
validated Foundation build artifacts instead of rebuilding the full XML-enabled
Foundation graph. Manual `_CFXMLInterface` and FoundationXML Swift source
handoff produced and signed `libFoundationXML.so`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/foundationxml-irhandoff-20260802-214017.log
/storage/Users/currentUser/swift-mainline-ohos-src/logs/relink-foundationxml-probe2-20260802-214626.log
LINK_RC=0
SIGN_RC=0
```

`import FoundationXML` typechecking and two executable smokes then passed:

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

The lzma boundary was closed for this probe by using the already-published
`xz/5.6.2` Conan cache package:

```text
/storage/Users/currentUser/.conan2/p/xz22c09c364bc26/p/include/lzma.h
/storage/Users/currentUser/.conan2/p/xz22c09c364bc26/p/lib/liblzma.a
/storage/Users/currentUser/swift-mainline-ohos-src/logs/probe-lzma-import-with-xz-cache-env-20260802-221415.log
TYPECHECK_RC=0
```

Full direct `unxip` typechecking passed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/typecheck-unxip-direct-parseaslib-20260802-222300.log
TYPECHECK_RC=0
```

The normal SwiftPM unxip release package still has a hang/process orchestration
blocker:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/unxip-spm-release-irhandoff-j2-20260802-223538-b64.log
swift-build slept in do_rt_sigsuspend with no frontend child and no log growth.
BUILD_STOPPED_BY_CODEX
```

A direct Swift 6 optimized unxip binary was then built through the same proven
IR handoff:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/unxip-direct-swiftc-irhandoff-concurrencyfix2-20260802-225605.log
[ohos-irhandoff] emit-ir rc=0 size=3656085
[ohos-irhandoff] opt rc=0
[ohos-irhandoff] clang rc=0 object-size=903152
BUILD_RC=0
SIGN_RC=0
HELP_RUN_RC=0
```

The output executable is:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/unxip-direct-irhandoff-20260802-225607
```

Binary audit shows `/lib/ld-musl-aarch64.so.1`, RUNPATH to the staged
Swift/Foundation/Dispatch/libxml2/xz paths, and expected NEEDED entries for
Swift runtimes, `libFoundationXML.so`, `libFoundation.so`,
`libswiftDispatch.so`, `libdispatch.so`, `libz.so`, `libxml2.so.16`, and
`libc.so`.

Conclusion update: Swift/OHOS is now strong enough to build a real optimized
unxip executable directly. Remaining work is to formalize the SwiftPM process
path and convert IR handoff, modulewrap, runtime staging, signing, SDK
propagation, symlink materialization, and Swift 6 actor-isolation source fixes
from diagnostics into reviewable recipe/toolchain behavior.

## 2026-08-02 SwiftPM unxip Release Success

The earlier SwiftPM process pause was not a confirmed permanent hang. A
single-job, single-frontend-thread SwiftPM release build was allowed to run
through its slow driver/helper probes and completed:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/unxip-spm-release-irhandoff-longmon-j1-t1-20260802-234731.log
Build complete! (211.85s)
[ohos-irhandoff] emit-ir rc=133 size=5863471
[ohos-irhandoff] opt rc=0
[ohos-irhandoff] clang rc=0 object-size=699192
```

The produced executable:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/tmp/unxip-3.3-src/.build/aarch64-unknown-linux-ohos/release/unxip
```

passed the true-device help smoke with `HELP_RC=0` and audited as an
OHOS/aarch64 musl executable with expected Swift/Foundation/Dispatch runtime
dependencies. The delivery boundary is now formalization: the successful path
still depends on experimental IR handoff, modulewrap handling, SDK/resource
propagation, runtime staging, signing, symlink materialization, and Swift 6
source compatibility patches before it can be treated as a clean Conan CI pass.

## 2026-08-03 unxip Conan create/test_package pass

The unxip recipe was then exercised through Conan on the true device. The first
Conan run reached real Swift source compilation and exposed one additional
Swift 6 continuation isolation diagnostic in `PermissiveActionLink.next()`.
The recipe now patches that four-tab `queued.append(continuation)` form in
both the top-level `unxip.swift` and the materialized `Sources/libunxip` copy.

The follow-up monitored run built both optimized Swift targets through the
experimental OHOS IR handoff and linked the SwiftPM release executable:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/conan-create-unxip-swiftpm-irhandoff-20260803-004816.out
[ohos-irhandoff] emit-ir rc=133 size=7852463
[ohos-irhandoff] opt rc=0
[ohos-irhandoff] clang rc=0 object-size=916096
[ohos-irhandoff] emit-ir rc=133 size=5863283
[ohos-irhandoff] opt rc=0
[ohos-irhandoff] clang rc=0 object-size=699192
Build complete! (456.70s)
Package '15141ce3eb5a91ba7d0b3075840da216efff4f0c' created
```

The created package revision is:

```text
unxip/3.3@ohpcd/stable#f9fcc576fbe5befb3433e94facae4f04:15141ce3eb5a91ba7d0b3075840da216efff4f0c#e6fb8470213a704b353d7c0a80add145
```

The first test_package failure was a fixed-shell-path issue
(`/data/service/hnp/bin/bash` absent), not a Swift/runtime failure. After
making the test package select an available shell and making `test.sh` POSIX-sh
compatible, standalone `conan test` printed `unxip 3.3` with `TEST_RC=0`.
A cached full `conan create` rerun then completed test_package with
`CREATE_RC=0`:

```text
/storage/Users/currentUser/swift-mainline-ohos-src/logs/conan-test-unxip-swiftpm-irhandoff-20260803-0104-test.out
/storage/Users/currentUser/swift-mainline-ohos-src/logs/conan-create-unxip-swiftpm-irhandoff-20260803-0105-full-create.out
```

The packaged binary passed `--version` and `--help` smokes. `llvm-objdump -p`
reports the OHOS musl loader string `/lib/ld-musl-aarch64.so.1`, RUNPATH to
the staged Swift/Foundation/Dispatch runtimes and Conan libxml2/xz package
paths, and NEEDED entries for Swift runtime libraries, Dispatch,
Foundation/FoundationXML, and `libc.so`.

This changes the unxip package boundary: unxip/3.3 itself now has true-device
Conan create/test_package evidence under the experimental Swift 6.0.3 OHOS
path. The remaining high-difficulty work is still at the toolchain/product
integration layer: remove or formalize probe wrappers, optimized IR handoff,
modulewrap behavior, SDK/resource propagation, runtime staging, signing, and
SwiftPM/SwiftDriver installation so clean CI can reproduce the result.
