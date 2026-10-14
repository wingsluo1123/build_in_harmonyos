# wasi-libc

libc for WebAssembly programs built on WASI system calls; packaged as a
from-source-built `wasm32-wasip1` sysroot.

## OpenHarmony PC status

| Version | Status | Notes |
| --- | --- | --- |
| 0.0-git20260129.ec0effd | built | Cross-built to wasm32-wasip1 on OHOS aarch64 via statically-linked `zig cc` (no OHOS clang ships the WebAssembly backend); upstream test suite executed with Node.js built-in WASI. |

## Upstream

- Source: https://github.com/WebAssembly/wasi-libc (commit `ec0effd`)
- Builtins (linked into libc.so): official wasi-sdk-25 compiler-rt archive
