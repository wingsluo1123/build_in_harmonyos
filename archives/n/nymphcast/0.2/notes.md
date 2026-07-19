# nymphcast 0.2 adaptation notes

## Source

- Upstream archive: `v0.2-alpha0`
- URL: `https://github.com/MayaPosch/NymphCast/archive/refs/tags/v0.2-alpha0.tar.gz`
- SHA-256: `528a0011f72f172f35f86221c4d7cc0854e8f6868bf78c95fc2bef02b5d448ee`

The package keeps the requested Conan reference `nymphcast/0.2` while using
the upstream alpha tag that is available for the 0.2 release line.

## Packaging

- Build system: CMake through Conan 2
- Package type: application
- Expected executables: `nymphcast` and `nymphcast_server`
- `commands.json` declares `nymphcast/0.2` as a tool package.

## Consumer test

The test package uses `VirtualRunEnv`, runs `nymphcast_server --version`, and
requires the output to contain the `NymphCast version` banner. It does not
mask command failures.

## Status

The recipe parses with Conan 2 and the source metadata is internally
consistent. The HarmonyOS cross-build is verified by PR CI.

<!-- ARCHIVE-CLOSED -->
