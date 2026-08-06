# git-cliff

A highly customizable changelog generator — see your git history in style.

- **Homepage**: https://github.com/orhun/git-cliff
- **License**: MIT OR Apache-2.0
- **Build system**: Cargo (Rust)
- **Type**: Command-line tool (application)

## OHOS Adaptation

git-cliff is a Rust/Cargo project that builds natively on OpenHarmony without source modifications. The key requirements are:

1. **Rust toolchain**: Install via Harmonybrew (`brew install rust`)
2. **Cargo mirror**: Configure rsproxy.cn mirror for crates.io access
3. **cc/c++ symlinks**: Create symlinks to clang/clang++ for the linker

## Version 2.10.1

- **Status**: published
- **Build date**: 2026-06-17
- **Build command**: `cargo build --release`
