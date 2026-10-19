pg_ivm 1.15 package for HarmonyOS PC (OHOS aarch64)

Prebuilt package layout (conan package `pg_ivm/1.15@ohpcd/stable`):

  lib/pg_ivm.so                 extension shared library (ELF64, loaded by postgres)
  extension/pg_ivm.control      extension control file (default_version = 1.15)
  extension/pg_ivm--*.sql       17 scripts: baseline 1.10 + 1.10→1.15 update chain
  upstream/                     vendored upstream tree used by test_package (pg_regress oracles)
  licenses/LICENSE              upstream license (PostgreSQL)

Runtime requirement: PostgreSQL 18.3 server (OHOS aarch64) — the software the
extension is loaded into. The recipe bootstraps PostgreSQL 18.3 from official
sources (with the HarmonyOS adaptation patch) to provide PGXS, server headers,
server binaries and the regression drivers; the published conan package
`postgresql/18.3` only ships the client side (no include/server, no lib/pgxs).

Install into a PostgreSQL cluster (extension files go to the PG layout):

  install -m 755 lib/pg_ivm.so      <pkglibdir>/pg_ivm.so
  install -m 644 extension/pg_ivm.* <sharedir>/extension/
  psql -c 'CREATE EXTENSION pg_ivm'

Verification: 13/13 upstream regression groups pass (4 pg_regress +
9 pg_isolation_regress); see ../reports/test-report.md.

Reproducing the verification
----------------------------
The test_package drives a temporary PostgreSQL 18.3 cluster that the recipe
bootstraps on the device (tmpfs /data/storage/el2/base/.pg_ivm-build) during
`build()`: that tree provides postgres/initdb/pg_ctl plus the pg_regress and
pg_isolation_regress drivers the upstream `make installcheck` target needs.
The published `postgresql/18.3` conan package cannot serve this purpose (it
ships the client side only). So on a fresh machine run, in order:

    conan create archives/p/pg_ivm/1.15 -pr:h=ci/conan/profiles/ohos-aarch64 \
        --build=missing          # bootstraps PG 18.3, builds, then tests
    conan test archives/p/pg_ivm/1.15/test_package pg_ivm/1.15@ohpcd/stable \
        -pr:h=ci/conan/profiles/ohos-aarch64   # re-runs only the test

`test_package` fails loudly (not silently) when the bootstrapped tree is
absent, naming the missing server binary.
