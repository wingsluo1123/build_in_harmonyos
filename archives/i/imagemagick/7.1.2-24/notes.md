# ImageMagick 7.1.2-24 adaptation notes

- Build system: Autotools
- Status: built
- Source: official ImageMagick release archive
- Source SHA256: `e44e70aa49e97ceb8b4f68e97829d0bde69b79387d69660b8886b1f6e06ddb19`

The recipe builds the command-line utilities and static ImageMagick libraries.
All optional delegates are disabled so the package has no unpublished Conan
dependencies. The built-in `xc:` and `txt:` coders remain available and are
used by the consumer smoke test.

The Conan run environment points `MAGICK_HOME` and `MAGICK_CONFIGURE_PATH` at
the package root so the executable loads its packaged policy, color, and type
configuration instead of probing the device's system `/etc` directory.

HarmonyOS-specific handling is limited to two reproducible patches:

1. `config.guess` maps the runtime system name to `*-unknown-linux-ohos`.
2. `configure` creates its temporary directory with an HMDFS-compatible umask.

The target tuple, compilers, flags, prefix, and staging paths come from Conan's
`AutotoolsToolchain`; the recipe does not hard-code device paths or `--host`.
