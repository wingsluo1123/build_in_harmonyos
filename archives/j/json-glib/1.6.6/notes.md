# json-glib 1.6.6 Conan Adaptation Notes

## Overview

json-glib is a JSON serialization/deserialization library for GLib, using the Meson build system. This adaptation creates a Conan recipe for HarmonyOS PC (aarch64).

## Version Info

- Version: 1.6.6
- Build system: Meson
- Adaptation date: 2026-08-06

## Source

- URL: https://repo.huaweicloud.com/gnome/sources/json-glib/1.6.6/json-glib-1.6.6.tar.xz
- SHA256: 96ec98be7a91f6dde33636720e3da2ff6ecbb90e76ccaa49497f31a6855a490e

## Conan Recipe Approach

### Dependencies

json-glib depends on GLib (glib-2.0, gio-2.0, gobject-2.0, etc.). The glib2/2.88.0 Conan package provides all these libraries in a single package.

### Key Adaptations

1. **glib2 .pc file fix**: The glib2 Conan package declares only `pkg_config_name="glib-2.0"`, so PkgConfigDeps generates only `glib-2.0.pc`. But json-glib's meson.build needs `gio-2.0`, `gobject-2.0`, etc. The glib2 package ships these .pc files in `lib/pkgconfig/` with `prefix=/` (broken). The recipe copies them to the generators folder with the correct prefix.

2. **glib-mkenums PATH**: meson's `gnome.mkenums()` calls `glib-mkenums` which is in glib2's `bin/` directory. The recipe adds this to PATH in `generate()`.

3. **GNU binutils pinning**: Same as glib2 — pin real `ar`, `as`, `strip`, `nm`, `ranlib` by absolute path because CI exports llvm-* names not on PATH.

4. **basic_layout**: The OHOS-adapted Conan lacks `meson_layout`; use `basic_layout` instead.

### Build Configuration

- Static library (`default_library=static`)
- Introspection disabled
- gtk_doc disabled
- Tests disabled
- Man pages disabled

## Build Artifacts

- Static library: `libjson-glib-1.0.a`
- Headers: 13 `.h` files in `include/json-glib-1.0/json-glib/`
- pkg-config: `json-glib-1.0.pc`
- Tools: `json-glib-validate`, `json-glib-format`

## Verification

- conan-verify: ✅ PASS (G0-G4, L2/L4/L5)
- W3 local CI simulation: ✅ PASS
- test_package: ✅ PASS (JSON parse + field access test)

---
**Adaptation complete**
**Final status**: published

**编译结束**
