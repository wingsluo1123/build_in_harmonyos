# just

> Just a command runner — a handy way to save and run project-specific commands.

## Description

`just` is a command runner that allows you to define and run project-specific commands,
similar to `make` but with a simpler syntax. It reads from a `justfile` (or `Justfile`)
and executes the defined recipes.

- **Homepage**: https://github.com/casey/just
- **License**: MIT
- **Language**: Rust
- **Build System**: Cargo

## Versions

| Version | Status | Date |
|---------|--------|------|
| 1.43.1  | built  | 2026-07-01 |

## OHOS Adaptation Notes

just is a Rust project. On OHOS, `rustc 1.87.0` segfaults (SIGSEGV), making source
compilation impossible. The pre-compiled `aarch64-unknown-linux-musl` static binary
from GitHub releases is used instead, loaded via `elfldr` (a custom ELF loader with
OHOS-compatible signature).

### Key Decisions
- **Build strategy**: Pre-compiled musl binary + elfldr wrapper
- **Binary source**: GitHub releases (aarch64-unknown-linux-musl)
- **Mirror**: ghfast.top for GitHub download acceleration (E017)
- **Loader**: elfldr (required for OHOS ELF signature compatibility)

### Dependencies
- `elfldr` — OHOS ELF loader for musl static binaries
