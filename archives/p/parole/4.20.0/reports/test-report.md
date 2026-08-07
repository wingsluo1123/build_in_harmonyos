# Test Report: parole 4.20.0 (OHOS aarch64)

## Build Information
- **Software**: parole 4.20.0
- **Target**: aarch64-unknown-linux-ohos
- **Compiler**: clang 15.0.4
- **Build Date**: 2026-08-07
- **Build System**: meson
- **Source**: https://github.com/xfce-mirror/parole/archive/refs/tags/parole-4.20.0.tar.gz

## Conan Recipe
- **conanfile.py**: ✅ Created (Meson build system, application type)
- **conandata.yml**: ✅ Created (SHA256 verified)
- **test_package/**: ✅ Created (CMake-based test, MANIFEST.yml)
- **commands.json**: ✅ Created (parole executable declared)

## Dependency Analysis

### Available Dependencies
| Dependency | Source | Version |
|-----------|--------|---------|
| glib | Conan repo | 2.84.0.1 |
| cairo | cmd-pkg | 1.18.2 |
| pango | cmd-pkg | 1.50.14 |
| gdk-pixbuf | cmd-pkg | 2.42.12 |
| harfbuzz | cmd-pkg | 14.2.0 |
| freetype | cmd-pkg | 2.14.3 |
| fontconfig | cmd-pkg | 2.16.0 |
| atk | cmd-pkg | 2.38.0 |
| libepoxy | cmd-pkg | 1.5.10 |
| dbus | cmd-pkg | 1.14.10 |
| gstreamer | cmd-pkg | 1.28.3 |
| gst-plugins-base | cmd-pkg | 1.28.3 |

### Missing Dependencies (not in Conan repo or cmd-pkgs)
| Dependency | Required Version | Status |
|-----------|-----------------|--------|
| gtk+-3.0 | >= 3.22.0 | ❌ cmd-pkg 3.24.38 returns 404 |
| dbus-glib-1 | >= 0.70 | ❌ Not available |
| libxfce4ui-2 | >= 4.16.0 | ❌ Not available |
| libxfce4util-1.0 | >= 4.16.0 | ❌ Not available |
| libxfconf-0 | >= 4.16.0 | ❌ Not available |

## Build Result

### Conan Verify (conan create)
- **Status**: ❌ Not passed (dependency_missing)
- **Reason**: Required dependencies not published to artifact repository

## Test Summary
- **Overall**: ❌ BUILD BLOCKED — Missing dependencies (gtk3, dbus-glib, XFCE libraries)
- **Conan Recipe**: ✅ Created with correct dependency declarations
- **Recommendation**: Adapt and publish missing dependencies first:
  1. gtk/3.24.38 (needs cairo, pango, gdk-pixbuf, atk, etc. — mostly available)
  2. dbus-glib/0.112 (needs dbus, glib — both available)
  3. libxfce4util/4.20.0 (needs glib — available)
  4. xfconf/4.20.0 (needs glib, dbus — both available)
  5. libxfce4ui/4.20.0 (needs gtk3, libxfce4util, xfconf)
