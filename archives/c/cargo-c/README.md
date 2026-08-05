# cargo-c — Rust Cargo Subcommand for C-Compatible Libraries

## Description
cargo-c is a helper program to build and install c-like libraries from Rust crates. It provides cargo subcommands that automate the generation of C API headers, pkg-config files, and static/shared library builds.

## Binaries
- `cargo-capi` — Build and install C-compatible libraries
- `cargo-cbuild` — Build C-compatible libraries
- `cargo-cinstall` — Install C-compatible libraries
- `cargo-ctest` — Test C-compatible libraries

## Dependencies
- Rust toolchain (cargo/rustc)
- OpenSSL (libssl, libcrypto)
- libz

## Versions
| Version | Status | Date |
|---------|--------|------|
| 0.10.18 | built | 2026-08-06 |
