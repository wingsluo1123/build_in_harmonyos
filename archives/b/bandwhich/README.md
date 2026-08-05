# bandwhich

Display current network utilization by process, connection and remote IP/hostname.

bandwhich is a terminal-based CLI tool written in Rust that sniffs network
traffic and displays real-time bandwidth usage broken down by process,
connection, and remote IP/hostname.

## Build System

- **Language**: Rust
- **Build tool**: Cargo (`cargo build --release`)
- **Dependencies**: libpcap (system), pnet/procfs (Cargo-managed Rust crates)

## HarmonyOS Adaptation

- Added `target_os = "ohos"` to `cfg()` conditions in `Cargo.toml`, `src/os/mod.rs`,
  and `src/os/shared.rs` to enable the Linux code paths on HarmonyOS.
- Added `#![cfg_attr(target_os = "ohos", allow(unexpected_cfgs))]` to suppress
  cfg-check warnings for the `ohos` target_os value.
- Uses `clang` as the linker (configured via `.cargo/config.toml`).
- Uses USTC cargo mirror for crates.io index and downloads.

## Versions

| Version | Status |
|---------|--------|
| 0.23.0  | built |
