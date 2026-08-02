# Swift OHOS helper scripts

`monitor-device.sh` is the low-impact process and memory check used before
starting any Swift build step on the shared HarmonyOS true device.

`swift-irhandoff-wrapper.c` is the source form of the experimental wrapper used
for the current optimized-object handoff. It delegates normal invocations to the
real `swiftc`/`swift-frontend`, but for optimized frontend object emission it
emits Swift IR first and then asks the OHOS LLVM `clang-15` path to produce the
final object. The wrapper intentionally reads real tool, sysroot, resource-dir,
and arch-module paths from environment variables or the packaged toolchain
layout; no signed ELF wrapper or probe-machine absolute path is stored here.
