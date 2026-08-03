# Swift OHOS helper scripts

`source-bootstrap-ohos.sh` is the reviewable entrypoint for rebuilding the
current OHOS Swift stage from source. Conan `source()` downloads and verifies
the Swift 6.0.3 component tarballs, applies the exported patches, then `build()`
invokes this script by default. The script recreates the probe layout under a
Conan build directory, validates the OHOS clang wrapper, sysroot, CMake/Ninja,
and pinned OHOS LLVM CMake package, builds cmark, configures the OHOS Swift
stdlib/compiler path, builds the requested Ninja targets, runs SwiftPM's
`Utilities/bootstrap install` when `swift-build`/`swift-package` are not already
present, and finally calls `assemble-stage-ohos.sh`. It defaults to
`SWIFT_OHOS_JOBS=2`; set
`SWIFT_OHOS_LLVM_BUILD_DIR`, `SWIFT_OHOS_CC`, `SWIFT_OHOS_CXX`, and
`OHOS_SYSROOT`/`OHOS_SDKROOT` explicitly in a clean CI worker.
When GitHub access is unstable, set `SWIFT_OHOS_SOURCE_TARBALL_DIR` to a
directory containing the official tarball basenames from `conandata.yml`; the
recipe still verifies every archive against the recorded sha256 before
extracting it.

`assemble-stage-ohos.sh` assembles a package-ready Swift OHOS stage from a
completed source-bootstrap workspace. It copies a real `bin/` toolchain,
including the `swift-frontend` and `swift-autolink-extract` helpers needed for
real compilation, `lib/swift`, and optional runtime `.so` inputs into a fresh
stage directory. It optionally signs ELF files and writes `STAGE-MANIFEST.txt`
for review. The script is driven by environment variables such as
`SWIFT_OHOS_BOOTSTRAP_ROOT`,
`SWIFT_OHOS_BIN_DIR`, `SWIFT_OHOS_SWIFTPM_BIN_DIR`,
`SWIFT_OHOS_SWIFTPM_LIB_DIR`, `SWIFT_OHOS_SWIFT_DRIVER_LIB_DIR`,
`SWIFT_OHOS_LIB_SWIFT_DIR`, `SWIFT_OHOS_RUNTIME_DIRS`, and
`SWIFT_OHOS_STAGE_OUT`. If no dynamic `libtinfo.so.6` is available, it can build
a minimal compatibility shim for the SwiftPM/Driver terminal-capability symbols
used by the current OHOS-native toolchain.

`swift-driver-new` is not copied by default because the current true-device
stage still hangs when `swift --version` dispatches through the new driver.
Set `SWIFT_OHOS_INCLUDE_DRIVER_NEW=1` only for targeted SwiftDriver debugging;
the default stage uses the already validated legacy driver path.

`monitor-device.sh` is the low-impact process and memory check used before
starting any Swift build step on the shared HarmonyOS true device.

`swift-irhandoff-wrapper.c` is the source form of the experimental wrapper used
for the current optimized-object handoff. It delegates normal invocations to the
real `swiftc`/`swift-frontend`, but for optimized frontend object emission it
emits Swift IR first and then asks the OHOS LLVM `clang-15` path to produce the
final object. The wrapper intentionally reads real tool, sysroot, resource-dir,
and arch-module paths from environment variables or the packaged toolchain
layout; no signed ELF wrapper or probe-machine absolute path is stored here.
