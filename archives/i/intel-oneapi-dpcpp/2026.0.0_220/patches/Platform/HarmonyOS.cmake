# Minimal CMake platform module for HarmonyOS (HongMeng kernel, Linux ABI).
# HarmonyOS user-space is Linux-compatible (aarch64-unknown-linux-ohos),
# so reuse Linux platform flags and mark UNIX.
set(UNIX 1)
include(Platform/Linux)
