# sqlsmith 1.5 HarmonyOS PC adaptation notes

## Scope and provenance

- Package name and version: sqlsmith/1.5.
- Upstream project: anse1/sqlsmith (random SQL query generator / fuzzer).
- Upstream source: official GitHub release tag v1.5:
  https://github.com/anse1/sqlsmith/archive/refs/tags/v1.5.tar.gz.
- Source SHA-256: 828ee3e816b94848627e8132d32ade6339dbcbba5469437dc9a6a8335d4dab23.
- License: GPL-3.0-only.

sqlsmith is a **command-line tool** (a single `sqlsmith` executable) that
connects to a live RDBMS and mass-generates random SQL to fuzz the target.
Upstream supports PostgreSQL (core DUT), SQLite and MonetDB (optional
`find_package` probes). It produces an executable, not a library, so the
recipe is `package_type="application"` with `commands.json` and a binary
(non-library) test_package.

## Dependencies (W0 / W0b analysis)

sqlsmith has three **hard** build dependencies, all already adapted and
published in this repository's OHOS registry:

| Dependency | Version | Why required | Provided target |
|-----------|---------|--------------|-----------------|
| libpq (PostgreSQL client) | 18.1 | postgres.cc / postgres.hh use the libpq C API (`PQ*`, `<libpq-fe.h>`) | `libpq::libpq` |
| libpqxx (C++ PostgreSQL client) | 8.0.1 | postgres.hh uses `pqxx::connection` | `libpqxx::pqxx` |
| Boost.Regex | 1.84.0 | `log.cc`/`monetdb.cc`/`sqlite.cc`/`sqlsmith.cc` include `<boost/regex.hpp>` **unconditionally** | `boost1.84-regex::boost1.84-regex` |

- libpqxx/8.0.1 already `requires libpq/18.1`; sqlsmith declares `libpq/18.1`
  explicitly (it uses libpq directly) so the dependency graph keeps a single
  consistent libpq version (no version conflict).
- libpqxx 8.x requires C++20; the libpqxx/8.0.1 recipe already forces C++20
  and this recipe does the same via the CMakeToolchain cppstd block (the
  shared OHOS profile pins `compiler.cppstd=17`).
- The OHOS `_LIBCPP_ENABLE_EXPERIMENTAL` + `-lc++experimental` flags that
  libpqxx consumers need are propagated automatically through the
  `libpqxx::pqxx` component in CMakeDeps.

Optional DUTs (SQLite / MonetDB) are left as upstream probes (disabled when
the corresponding library is not present), matching upstream's minimal
PostgreSQL-only build.

## Build

The recipe uses the CMake build (CMakeLists.txt, project SQLsmith):

1. `get()` the official v1.5 tarball (strip_root).
2. Apply `patches/0001-cmakelists-deps.patch`.
3. `CMakeToolchain`: force `cmake_system_name=OHOS` /
   `cmake_system_processor=aarch64` and C++20 std level; `CMakeDeps` for the
   three requires.
4. `cmake.configure(); cmake.build()`.
5. `package()`: sqlsmith's CMakeLists.txt has **no `install()` rule**, so the
   built `sqlsmith` binary is copied manually into `package/bin` (same pattern
   as abcm2ps in this registry).

## Source patch

`patches/0001-cmakelists-deps.patch` rewrites the CMake dependency-discovery
section only (no source-code changes):

- Replace `target_link_libraries(sqlsmith PostgreSQL::PostgreSQL)` +
  `find_package(PostgreSQL REQUIRED)` with `find_package(libpq CONFIG
  REQUIRED)` + `target_link_libraries(sqlsmith libpq::libpq)`.
- Replace the `find_package(PQXX REQUIRED)` / `PQXX::PQXX` /
  `USE_UPSTREAM_LIBPQXX` FetchContent branches with
  `find_package(libpqxx CONFIG REQUIRED)` + the Conan `libpqxx::pqxx` target;
  set `HAVE_LIBPQXX8`.
- Replace the `if(NOT std_regex_ok)` Boost gate with an **unconditional**
  `find_package(boost1.84-regex CONFIG REQUIRED)` + `boost1.84-regex::boost1.84-regex`
  and set `HAVE_BOOST`/`HAVE_BOOST_REGEX`, because the core sources use
  `<boost/regex.hpp>` without a guard (the upstream `std::regex` probe can pass
  without making Boost available, which would then fail to compile).

The patch applies cleanly with `patch -p1` and reproduces the verified
modified CMakeLists.txt (round-trip checked locally).

## Upstream test inventory (R51)

sqlsmith 1.5 upstream has **no automated test suite**. Audited the official
v1.5 release archive:

- No `tests/` or `test*` directory.
- CMakeLists.txt: no `add_test` / `enable_testing` / CTest usage.
- Makefile.am: no `check_PROGRAMS` / `TESTS` / `check` target.
- configure.ac: no test-framework detection, no `AC_CONFIG_TESTDIR`.
- The only CI (`.github/workflows/regression.yml`) "test" step is
  `pg_virtualenv build/sqlsmith --max-queries=100 --verbose` — an un-asserted
  smoke run against a live PostgreSQL that cannot run without a database
  server, so it is not countable as an upstream test case.

Therefore `upstream_tests_exist: false`, `upstream_test_total: 0`,
`upstream_test_count_method: manual_audit` (see test_package/MANIFEST.yml for
the full audit).

*The functional behavior (random SQL generation) fundamentally requires a live
RDBMS to produce queries, so no offline upstream test can be run on the target
either; the runnable consumer coverage is the installed binary's `--version` /
`--help` smoke test in test_package.*

## test_package (consumer view)

test_package is the executable-style consumer test (not a library link test):

- Runs the installed `sqlsmith` binary in the conanrun environment (so its
  shared libpq.so resolves) via `test.sh`.
- Two substantive checks, each printing a `TEST PASS:` marker:
  1. `sqlsmith --version` exits 0 and reports `SQLsmith`;
  2. `sqlsmith --help` exits 0 and lists the CLI options (incl. `--version`).
- Emits `HMBS_UPSTREAM_TEST_RESULT` (status=no_tests, discovered/executed=0)
  and `HMBS_TEST_PACKAGE_RESULT` (discovered=2, passedCount counted from the
  real `TEST PASS:` markers in test.sh output).

## HarmonyOS device verification

- Environment: HarmonyOS HongMeng Kernel aarch64, clang 15.0.4 (libc++ 15),
  Conan 2.x, profile `ci/conan/profiles/ohos-aarch64`.
- Command: `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`.
- Status: **待真机 evidence 轮验证** (this working tree has not yet been
  validated on a real HarmonyOS device; the HMBS preflight will run it and
  record the real result / counts).

## Known limits

- SQLite / MonetDB DUTs are not enabled (optional upstream probes; a
  PostgreSQL-only build is a complete, working core product).
- The built binary carries a blank git revision in `--version`/`--help` banner
  (upstream runs `git describe` in the source tree, which is absent after the
  conan `get()`; it degrades gracefully to `SQLsmith `).
- Random SQL generation requires a live PostgreSQL/SQLite/MonetDB server and
  is intentionally exercised only as `--version`/`--help` smoke coverage here.
