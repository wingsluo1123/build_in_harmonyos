# aconnectgui 0.9.0rc2-1

FLTK-based GUI frontend for ALSA aconnect utility.

## Build notes

- Source tarball lacks pre-generated configure; autoreconf output shipped in `preconf/`.
- No config.sub/config.guess needed (configure doesn't canonicalize triplets).
- Depends on fltk/1.4.5 (X11 backend) and alsa-lib/1.2.12.
- `package_type = "application"` — installs a single `bin/aconnectgui` binary.
- COPYING file manually created (missing from upstream).
- Preconf files touched after overlay to prevent `make` from re-running autoreconf.
- ac_fn_c_try_link function definition moved before its first use in preconf/configure (autoconf 2.71 bug with nested AC_CHECK_LIB).
- Shebang patching for OHOS (`/bin/sh` → `/system/bin/sh`, etc.) applied at build time (only on OHOS, not on Linux cross-build).
- HMDFS mktemp workaround applied at build time.
- Patch 0001: Fix implicit int on `main()` for C++17 compliance.
