# Test Report — crosstool-ng 1.28.0

## Build Environment
- Build system: autotools
- Compiler: clang 15.0.4
- Platform: OpenHarmony (aarch64)
- Build date: 2026-08-06

## Compilation
- configure: PASSED (all checks OK)
- make -j1: PASSED (no errors)
- make install DESTDIR: PASSED
- make check: PASSED (no tests to run)

## Verification
- ct-ng --version: GNU Make 4.4.1 (Built for aarch64-unknown-linux-gnu)
- conan create: PASSED (G2 clean build)
- W3 local CI simulation: PASSED

## Dependencies
- texinfo 7.3 (makeinfo) — installed via cmd-pkgs, Perl modules from source
- help2man 1.49.3 — installed via cmd-pkgs
- ncurses 6.4 — installed via cmd-pkgs (library), headers generated from source
- libtool 2.5.4 — installed via conan (ohpcd remote)

## Patches Applied
1. 0001-configure.patch — Fix umask 077 to 022 (HMDFS permission, E011)
2. 0002-scripts-config.guess.patch — Add HarmonyOS platform recognition (E007)
3. 0003-scripts-config.sub.patch — Add ohos triplet validation (E072)

## Notes
- crosstool-ng is a Make wrapper (ct-ng), not a typical binary
- texinfo prebuilt package incomplete (missing Perl modules), fixed by extracting modules from texinfo 7.3 source
- ncurses prebuilt package missing headers, generated from ncurses 6.4 source
- libtool installed via conan from ohpcd remote
