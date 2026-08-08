# fluent-bit — OpenHarmony OHOS adaptation

fluent-bit is a fast and lightweight log processor and forwarder, or
router, for collecting data from any input, enriching with metadata and
sending to multiple destinations. This archive contains the OpenHarmony
(aarch64 musl) adaptation recipe.

## Versions
- 5.0.9 (published, 2026-07-30): zero-external-dependency build

## Build strategy
All optional subsystems (TLS, HTTP server, AWS, SQLDB, Kafka, LuaJIT, WASM,
and all input/output/filter plugins requiring external libraries) are
disabled via CMake flags, bypassing R36. Stub headers are provided for
the unconditional core sources that still `#include <openssl/...>` /
`<sqlite3.h>` / `<fts.h>` (musl lacks BSD fts).

## Package layout
- `5.0.9/conanfile.py` — Conan 2.x recipe (application, 0 deps)
- `5.0.9/patches/` — source patch + stub sources (plain-text, no binary tar.gz)
- `5.0.9/test_package/` — L1 official test (runs the installed binary)
- `5.0.9/manifest.yaml` — version manifest
- `5.0.9/notes.md` — adaptation notes & lessons learned
