# docuum 0.27.0 – Adaptation Notes

## Summary
- **Project:** [docuum](https://github.com/stepchowfun/docuum) — a Rust Docker disk usage tool
- **License:** MIT
- **Build system:** Cargo (Rust)
- **Version:** 0.27.0

## Build steps
1. `cargo build --release` produces the binary `target/release/docuum` (or `docuum.exe` on Windows).
2. The binary is packaged to `bin/` in the Conan package folder.

## Adaptation details
- `package_type = "application"` — no libraries are exposed.
- `settings` include `os`, `compiler`, `build_type`, `arch` as required by Rust Cargo builds.
- Source is fetched from the GitHub tag archive and stripped of the enclosing directory.
- No extra system dependencies beyond a Rust toolchain (rustc, cargo).

## Status
- **Status:** built
- Tested locally with Rust 1.60+.
