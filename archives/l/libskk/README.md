# libskk

`libskk` provides a GObject-based Japanese kana-kanji conversion library and the `skk` command-line tool.

| Version | Status | Build system |
| --- | --- | --- |
| 1.1.1 | built | Autotools |

Homepage: https://github.com/ueno/libskk

The Conan package provides the library, public C and Vala interfaces, typing rules, and upstream `skk` utility. It requires GLib/GIO, libgee, json-glib, and libxkbcommon; Vala is a build tool. FEP, documentation, and optional GObject Introspection output are disabled for the HarmonyOS build. HarmonyOS builds use a static libskk archive because the platform's shared libgee embeds its own static GLib copy; linking libskk as shared as well causes duplicate GType registration. Conan run environments point `LIBSKK_DATA_PATH` at the package's installed rule data. The recipe works around stale `//lib` paths in platform Conan `.la` metadata with temporary build-local wrappers and leaves cached dependency files unchanged.
