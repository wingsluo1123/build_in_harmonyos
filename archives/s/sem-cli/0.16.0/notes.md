# sem-cli 0.16.0 — Adaptation Notes

## Build System
- Rust/Cargo project
- Workspace manifest at `crates/sem-cli/Cargo.toml`
- Build command: `CARGO_TARGET_DIR=target cargo build --release --manifest-path crates/sem-cli/Cargo.toml`

## Dependencies (R27: @ohpcd/stable)
- openssl/3.5.6@ohpcd/stable
- libgit2/1.9.4@ohpcd/stable

## Key Decisions
- Both openssl and libgit2 are conan-managed (not system-installed)
- LIBGIT2_DIR set from conan dependency package_folder
- OPENSSL_DIR set from conan dependency package_folder
- PKG_CONFIG_PATH includes both openssl and libgit2 pkgconfig paths

## R32 Compliance
- settings.os checked with `in ("Linux", "OHOS")` in generate()

## Quality Audit Fix (R27 + conandata.yml + conan-verify)
- Fixed R27 violation: added libgit2/1.9.4@ohpcd/stable as conan dependency
- Fixed conandata.yml: changed file:// URL to GitHub URL
- Removed hardcoded /storage/Users/currentUser/usr/local paths
- Used conan-managed libgit2 package_folder for LIBGIT2_DIR

---

**编译结束**: 2026-07-03 16:21
**最终状态**: built
