# cdk 5.0 adaptation notes

## Build environment
- Build system: autotools (configure + make)
- Build date: 2026-07-15
- Compiler: clang/clang++
- Platform: aarch64-unknown-linux-ohos (HarmonyOS PC)
- Status: published (Conan recipe scaffolding)

## Software info
- Name: cdk (Curses Development Kit)
- Upstream version: 5.0-20260119 (snapshot tag t20260119)
- Official site: https://dickey.his.com/cdk/cdk.html
- GitHub: https://github.com/ThomasDickey/cdk-snapshots
- License: BSD-4-Clause-UC
- Type: dependency (terminal widget development library)

## Build steps

1. conan source downloads the GitHub archive (tag t20260119)
2. Patch config.guess/config.sub for HarmonyOS platform support (E007)
3. ./configure --enable-static --disable-shared --prefix=...
4. make -j1
5. make install (DESTDIR staging)

## Dependencies

| Dependency | Version | Type |
|------------|---------|------|
| ncurses | 6.4 | required (curses library) |

## Build products
- Static library: libcdk.a
- Headers: cdk.h + cdk/*.h
- Config tool: cdk5-config

## test_package
- test_package.c: verifies cdk.h header can be included
- conanfile.py: compiles test program and runs it (L1 official test)

## Notes
- CDK provides predefined curses widgets (buttons, menus, scroll lists, dialogs, etc.)
- R26: static linking enforced for system-name libraries
- E007: config.guess/config.sub require HarmonyOS detection patches (applied at build time)
- HMDFS platform may need umask 077 -> 022 workaround in config.status

## File manifest
- conandata.yml - source URL + sha256 + patches
- conanfile.py - Conan 2.x autotools recipe
- test_package/conanfile.py - L1 test recipe (with build())
- test_package/test_package.c - header inclusion test
- manifest.yaml - version manifest
- notes.md - this file
- patches/.gitkeep - patches placeholder
