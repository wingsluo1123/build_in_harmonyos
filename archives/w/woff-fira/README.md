# WOFF Fira Code

Fira Code is a monospaced typeface for programming; this package provides the upstream WOFF webfont files for HarmonyOS PC applications.

## Contents

- Six WOFF files: Light, Regular, Medium, SemiBold, Bold, and the variable font.
- SIL Open Font License 1.1.

## HarmonyOS PC

This is a data-only webfont package. Conan installs the files under `share/fonts/woff-fira/woff`; applications can load them through CSS `@font-face` or the Web Font Loading API in WebView. The package does not install the fonts as system-wide native fonts and has no compiler or runtime dependencies.

## References

- Upstream: <https://github.com/tonsky/FiraCode>
- Release 6.2: <https://github.com/tonsky/FiraCode/releases/tag/6.2>
