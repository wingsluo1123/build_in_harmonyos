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

## Review Follow-up

The 2026-08-03 AI review P0/P2/P3 items were folded back into the staged patch
set:

- Removed the dangling empty `if` block in the ClangImporter CC1 argument
  filter.
- Scoped the SwiftPM `sigaction` member-layout change to `os(OHOS)` so Linux
  Glibc and Android keep their original branches.
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

## Next Steps

Do not start another heavy Swift build while other `conan create` jobs are
active on the true device. When the device is quiet:

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

Then continue with a low-concurrency staged packaging validation:

```sh
export SWIFT_OHOS_BOOTSTRAP_ROOT=$HOME/swift-mainline-ohos-src
export SWIFT_OHOS_STAGE_OUT=$SWIFT_OHOS_BOOTSTRAP_ROOT/swift-ohos-stage-$(date +%Y%m%d-%H%M%S)
export TMPDIR=$SWIFT_OHOS_BOOTSTRAP_ROOT/tmp
export SDKROOT=/storage/Users/currentUser/usr/local/sysroot
export OHOS_SYSROOT=$SDKROOT
export OHOS_SDKROOT=$SDKROOT
# Set SWIFT_OHOS_SIGN=1 only when the bootstrap outputs still need signing.
sh archives/s/swift/6.0.3/scripts/assemble-stage-ohos.sh

export SWIFT_OHOS_STAGED_ROOT=$SWIFT_OHOS_STAGE_OUT
conan create archives/s/swift/6.0.3 -pr:h ohos_4_1_armv8 -pr:b default -tf ""
conan create archives/s/swift/6.0.3 -pr:h ohos_4_1_armv8 -pr:b default
```

The current Conan recipe intentionally packages a supplied staged toolchain
rather than claiming a fully automated Swift source bootstrap. The
`assemble-stage-ohos.sh` helper is the first automation boundary for turning a
completed source-bootstrap workspace into a clean signed stage that can be
reused by Conan and downstream SwiftPM packages.

Current stage boundary: `swift-driver-new` is built but not copied into the
default packaged stage. When present, `swift --version` dispatches into the new
driver and hangs on the true device; without it, `swift`, `swiftc`,
`swift-build`, and `swift-package` all complete their version smoke through the
validated legacy driver path. Set `SWIFT_OHOS_INCLUDE_DRIVER_NEW=1` only for
the separate SwiftDriver follow-up investigation.
