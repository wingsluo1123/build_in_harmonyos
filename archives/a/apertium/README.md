# apertium

Apertium core engine — rule-based machine translation transfer, tagger,
formatters, and validators built atop lttoolbox, libxml2, ICU, and utfcpp.

The package installs `libapertium.a` plus the transfer / preprocess /
tagger / validate / deshtml / desrtf / desxml / etc. binaries under `bin/`.

Three portability patches adapt the upstream to OHOS + clang 15:
`getopt_long.h` skips a conflicting `extern int getopt()` redeclaration,
`tmx_builder.cc` inlines the `PACKAGE_VERSION` literal, and
`string_view.h` / `filesystem.h` force the C++17 standard headers
(`clang` 15 + `libc++` removed `<experimental/*>`).

The autotools recipe generates `apertium_config.h.in` from the shipped
CMake template (`apertium_config.h.cmake_in`) and copies the `*.xsl` /
`*-format*.xml` / `*.l` data files into the build folder so `xsltproc`
and `flex` recipes resolve during `make`.
