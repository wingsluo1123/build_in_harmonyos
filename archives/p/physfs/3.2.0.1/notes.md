# PhysFS 3.2.0.1 adaptation notes

## Version

- Upstream version: 3.2.0
- Conan recipe revision: 3.2.0.1
- Build system: CMake
- Target: HarmonyOS PC, AArch64

The `3.2.0` recipe is already published. R37 therefore requires the first
recipe correction to use the `3.2.0.1` suffix instead of replacing the
published recipe.

## Source

The source archive is the Debian official mirror's immutable copy of the
upstream `release-3.2.0` tag. It is used because the CI environment must not
depend on GitHub downloads.

- URL: `https://deb.debian.org/debian/pool/main/libp/libphysfs/libphysfs_3.2.0.orig.tar.gz`
- SHA256: `c0e718a1f5ba464570a383c12771879aeddb5dabcc3385acc5f14a4c26b93301`

## Build configuration

- Build the static library.
- Disable the shared library, upstream interactive utility, and Doxygen docs.
- Set `CMAKE_POLICY_VERSION_MINIMUM=3.5` for CMake 4 compatibility.
- No source patches are required.

## Test coverage

The consumer test links through Conan's generated `PhysFS::PhysFS` target and
checks initialization, header/runtime version agreement, the exact upstream
version, archive-format registration, and clean shutdown. Every failure path
prints a diagnostic before returning a distinct non-zero code.

Official HarmonyOS CI verification is pending for this recipe revision.
