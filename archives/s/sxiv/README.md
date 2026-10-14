# sxiv

Simple X image viewer (sxiv) is a lightweight keyboard-driven image viewer
built on Imlib2 and X11.  The HarmonyOS PC adaptation publishes a runnable
`sxiv` executable for OHOS aarch64.

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 26 | built | OHOS X11 drawable compatibility layer; no X display required for the packaged smoke test |

## Dependencies

The recipe uses the published OHPCD packages for libX11, libXft, fontconfig,
Imlib2, giflib and libexif.  The published Imlib2 package is intentionally
built without X11, so sxiv carries a small `libX11`-backed compatibility
object for the drawable rendering calls.  See `26/notes.md` for details.
