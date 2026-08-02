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

## Next Steps

Do not start another heavy Swift build while other `conan create` jobs are
active on the true device. When the device is quiet:

```sh
date
uptime
free -h
snapshot="${TMPDIR:-${HOME:-/tmp}/tmp}/codex-ps-swift-check.txt"
mkdir -p "$(dirname "$snapshot")" 2>/dev/null || true
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
export SWIFT_OHOS_STAGED_ROOT=/path/to/signed/swift-ohos-stage
conan create archives/s/swift/6.0.3 -pr:h ohos_4_1_armv8 -pr:b default -tf ""
conan create archives/s/swift/6.0.3 -pr:h ohos_4_1_armv8 -pr:b default
```

The current Conan recipe intentionally packages a supplied staged toolchain
rather than claiming a fully automated Swift source bootstrap. Source-bootstrap
automation remains the next review item after the staged package is reproducible
from a clean signed stage.
