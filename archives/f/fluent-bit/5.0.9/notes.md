# fluent-bit 5.0.9 progress

## Current route

The historical PR proved that a minimal binary can compile, but it was rejected
because the build disabled core dependencies and substituted stubs for
OpenSSL/sqlite3/TLS/SQLDB/HTTP behavior.  This branch uses the opposite route:
enable the highest-value core surfaces with real dependencies first.

## First-stage dependency set

- `openssl/3.5.6.1`: TLS and crypto/HMAC behavior.
- `sqlite3/3.49.1`: SQLDB behavior and tests that need a real sqlite backend.
- `libyaml/0.2.5`: YAML config format.
- `musl-fts/1.2.7`: BSD fts APIs used by chunkio on HarmonyOS musl.

`c-ares/1.34.6` is intentionally not forced in the first stage because Fluent
Bit 5.0.9 already vendors c-ares 1.34.6.  If DNS-related tests fail because of
the bundled path, switch to `FLB_PREFER_SYSTEM_LIB_CARES=On` later.

## Patch summary

- Top-level `CMakeLists.txt`: add generated monkey header include paths and an
  optional `FTS_INCLUDE_DIR`. It also normalizes Conan CMakeDeps' `OpenSSL_FOUND`
  spelling to the upstream `OPENSSL_FOUND` checks and adds the discovered
  OpenSSL include directory when TLS is enabled.
- `lib/chunkio/src/CMakeLists.txt`: link `chunkio-static` with the absolute
  `FTS_LIBRARY` when it is provided.
- `lib/monkey/mk_core/CMakeLists.txt`: add the generated monkey include dir.
- `src/CMakeLists.txt`: append absolute `OPENSSL_SSL_LIBRARY` and
  `OPENSSL_CRYPTO_LIBRARY` paths to `FLB_DEPS` when Conan provides them, and
  link `fluent-bit-bin` with the absolute `FTS_LIBRARY`. It also compiles the
  record-accessor runtime sources alongside `FLB_REGEX` without entering the
  Flex/Bison-generated `src/record_accessor` target.
- `src/record_accessor/flb_ra_parser.c`: remove generated lexer/parser header
  dependencies and use a simple non-Flex key parser for the first-stage build.
- `src/flb_blob_db.c`: keep the historical compile fix for the `FLB_SQLDB=Off`
  branch. This branch should not be exercised in the target build, but the fix
  is harmless and keeps alternate builds compiling.
- `src/flb_http_client.c`: include upstream node headers needed by strict C
  compilation.

The current OHOS pass enables `FLB_PARSER` but keeps the upstream
`FLB_RECORD_ACCESSOR` CMake option disabled. The true build showed that the
available `flex/2.6.4` package has `FlexLexer.h` and `libfl.a`, but no
`bin/flex`, while `bison/3.8.2` does provide `bin/bison`. Therefore this route
does not rely on Conan `tool_requires` for Flex/Bison. Instead it compiles the
record-accessor runtime sources directly and patches `flb_ra_parser_meta_create`
to parse simple top-level keys without generated Flex/Bison sources.
`FLB_STREAM_PROCESSOR` stays disabled for the first-stage build because it
broadens the parser-driven surface and is not needed for the initial binary
smoke test. Processor plugins are also disabled in this first pass because
`processor_sql` has its own Flex/Bison-generated parser path and pulled that
path into an earlier configure failure.

`FLB_SIGNV4` is disabled in the first build. The true device build showed that
`flb_signv4.c` and `flb_signv4_ng.c` require complete AWS credential/provider
and slist definitions, while the first-stage route deliberately keeps
`FLB_AWS=Off`. SignV4 should be restored together with the complete AWS surface,
not as an isolated flag.

The first-stage plugin set is now controlled with `FLB_MINIMAL=On`, followed by
explicit `FLB_IN_HTTP=On` and `FLB_OUT_HTTP=On`. This avoids default-on plugins
such as `in_tail`, which pulled parser/multiline/log-event implementation
details back into the build after those feature paths were intentionally
disabled.

## Static validation done

- `python -m py_compile` passed for recipe and test_package recipe.
- `git diff --check -- archives/f/fluent-bit` passed.
- Patch SHA in `conandata.yml` matches
  `patches/0001-ohos-real-deps-source-patches.patch`.
- `git apply --check` passed against an unpacked upstream v5.0.9 source tree.
- `conan export archives/f/fluent-bit/5.0.9` passed with an isolated
  `CONAN_HOME`; the latest local export after adding CTest execution is
  `fluent-bit/5.0.9#a3d1e4ff18ae5261d1a95ba2bf15c34e`.
- Registry API confirmed the first-stage dependency coordinates exist:
  `openssl/3.5.6.1`, `sqlite3/3.49.1`, `libyaml/0.2.5`, and `musl-fts/1.2.7`.

Local `conan graph info` with a throwaway Conan home did not resolve
`openssl/3.5.6.1` because that home only had ConanCenter configured and did not
include the ohpcd remote or locally exported dependency recipes.  This is an
environment limitation of the static check, not a recipe syntax failure.

## Upstream CTest validation

When `with_tests=True`, the recipe now runs real upstream CTest during
`build()` instead of relying on `test_package`.  It first prints the discovered
tests with `ctest -N --test-dir <build_folder>`, then executes the
`internal|runtime` labeled tests with:

```
ctest --test-dir <build_folder> --output-on-failure --timeout 180 -j1 --no-tests=error -L "internal|runtime"
```

`TMPDIR`, `TMP`, and `TEMP` are redirected to a build-folder test directory to
avoid OHOS `/tmp` write restrictions where upstream tests honor the environment.
The `with_internal_tests` and `with_runtime_tests` options allow the two CTest
layers to be toggled independently for follow-up audits.

Audit run r3 exposed one build-time upstream test boundary before CTest could
start: `flb-it-cumulative_to_delta` links against
`flb_cumulative_to_delta_ctx_*` symbols while
`FLB_PROCESSOR_CUMULATIVE_TO_DELTA=Off`.  It is excluded from the first-stage
subset until the corresponding processor surface is restored.

Audit run r4
(`/storage/Users/currentUser/ohos-test-runs/codex-a-fluent-bit-fluent-bit-5.0.9-upstream-ctest-r4-20260813-181605-41015`)
registered 94 tests after excluding `flb-it-cumulative_to_delta`, executed 82
`internal|runtime` tests, and produced 62 passes plus 20 failures.  The failed
tests were:

- runtime: `flb-rt-core-timeout`, `flb-rt-core_chunk_trace`,
  `flb-rt-in_http`, `flb-rt-core_routes`, `flb-rt-out_lib`.
- internal: `flb-it-pack`, `flb-it-sds`, `flb-it-router_config`,
  `flb-it-utils`, `flb-it-mp`, `flb-it-input_chunk`,
  `flb-it-input_chunk_routes`, `flb-it-processor`, `flb-it-conditionals`,
  `flb-it-strptime`, `flb-it-storage_inherit`, `flb-it-opentelemetry`,
  `flb-it-storage_dlq`, `flb-it-fstore`, `flb-it-reload`.

The first failure pass points to a mix of OHOS/platform and deliberate
first-stage feature boundaries: hard-coded `/tmp` paths in storage tests, tests
that require plugins outside the minimal matrix, timezone/UTF-8 behavior
differences, and a few crash paths that need a narrower source-level audit.

Experiment r5 tried widening the plugin matrix for several failed runtime and
processor cases (`dummy`, `emitter`, metrics, stdout/tcp, modify/grep/stdout).
It did not reach CTest: the larger static test link failed in OpenSSL
`libcrypto.a` with AArch64 `R_AARCH64_ADR_PREL_PG_HI21 out of range`
relocations.  Those plugin expansions are not part of the first-stage CI-safe
route.

Current passing run r6
(`/storage/Users/currentUser/ohos-test-runs/codex-a-fluent-bit-fluent-bit-5.0.9-upstream-ctest-r6-20260813-191748-26357`)
used recipe revision `fluent-bit/5.0.9#a3d1e4ff18ae5261d1a95ba2bf15c34e`.
It registered 74 tests with `ctest -N`, executed 62 labeled upstream CTests,
and passed all 62:

- Upstream CTest: 62/62 pass, 0 failed.
- Label summary: 53 internal tests, 9 runtime tests.
- Test time: 107.50 seconds.
- Full package reference:
  `fluent-bit/5.0.9#a3d1e4ff18ae5261d1a95ba2bf15c34e:7ac4253b0cf1136118245347b809b182922c12d6#16afc4af54f9b04df6b50ec2b57e416b`.

The `test_package` smoke still passes separately (`fluent-bit --version`,
`fluent-bit --help`, and its CTest wrapper 1/1), but it is package validation
only and is not counted as upstream coverage.

## Device build status

The true HarmonyOS `conan create` reached the source compile stage on
2026-08-12 and compiled to about 70%.  It then failed because `flb_hmac.c`,
`flb_hash.c`, and `flb_crypto.c` include `<openssl/err.h>` while the OpenSSL
package include path was not propagated into the `fluent-bit-static` compile
command.  The recipe now passes `OPENSSL_ROOT_DIR`, `OPENSSL_INCLUDE_DIR(S)`,
`OPENSSL_SSL_LIBRARY`, and `OPENSSL_CRYPTO_LIBRARY`; the source patch also
bridges Conan CMakeDeps' `OpenSSL_FOUND` variable to upstream's
`OPENSSL_FOUND` gate.

After that fix, the next true build reached about 76%. It failed in
`flb_cfl_ra_key.c`, `flb_cfl_record_accessor.c`, and `flb_conditionals.c`
because `FLB_REGEX=Off` removed regex definitions while those core objects still
compile regex-aware functions. The recipe now restores `FLB_REGEX=On` without
re-enabling the Flex/Bison parser, record accessor, stream processor, or
processor SQL paths.

The following run then reached the SignV4 objects. It failed because SignV4
uses AWS credential/provider structures while `FLB_AWS=Off` only leaves forward
declarations visible. The recipe now disables `FLB_SIGNV4` for the first-stage
real-dependency build.

The next run reached `plugins/in_tail`. Because `FLB_PARSER`,
`FLB_RECORD_ACCESSOR`, and related multiline paths are disabled, `in_tail`
encountered incomplete log-event encoder/decoder and multiline types. Rather
than chasing default-on plugins one by one, the recipe now enables
`FLB_MINIMAL=On` and turns on only the intended first-stage HTTP input/output
plugins.

With `FLB_MINIMAL=On`, the device build reached the final `fluent-bit` binary
link. It failed on `ld.lld: unable to find library -lfts` because the
`musl-fts` package provides `libfts.so.0.0.0` and `libfts.la`, but not an
unversioned `libfts.so` or static `libfts.a`. The recipe now passes an absolute
`FTS_LIBRARY`, and the source patch links both `chunkio-static` and
`fluent-bit-bin` against that path.

After the `FTS_LIBRARY` fix, the next true device build reached the final link
again. `musl-fts` was present on the link line, but the binary still failed
because `FLB_PARSER`/record-accessor runtime symbols were absent while core and
HTTP code still referenced them, and because the final link did not include
OpenSSL's static libraries. A follow-up tried `flex/2.6.4` and `bison/3.8.2` as
build tools; Bison worked, but the Flex package has no executable. The current
recipe now enables parser sources, compiles record-accessor runtime sources
without the generated target, and the patch appends Conan's absolute OpenSSL
library paths to `FLB_DEPS`.

The latest true device run completed the main package build, install, and
package creation. It then failed in `test_package` while executing
`fluent-bit --version`: the binary needs `libfts.so.0`, and Conan had generated
the correct `conanrun` environment with the `musl-fts` libdir in
`LD_LIBRARY_PATH`, but the test recipe did not run the probe under that
environment. The test recipe now executes `test_fluent_bit` with
`env="conanrun"` so the child `fluent-bit` process inherits the runtime library
path.

After that fix, the true HarmonyOS `conan create` passed on 2026-08-12. The
main package was created as
`fluent-bit/5.0.9#7457ffa948043d0a3846860bdaf1a457:85bcb60f2b3b1e629e700846417428a8dd72045b#a34129567a535bffb934db9ec34e31d9`,
and `test_package` successfully executed `fluent-bit --version`,
`fluent-bit --help`, and the single CTest probe under `conanrun`.
