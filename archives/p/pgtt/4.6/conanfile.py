#!/usr/bin/env python3
"""Conan recipe — pgtt 4.6 (PostgreSQL server extension, OHOS PC aarch64).

pgtt (PostgreSQL Global Temporary Tables) implements Oracle-style GLOBAL
TEMPORARY TABLES for PostgreSQL: a temporary table is mirrored, per session,
onto a permanent "template" table so that its definition (and its data, for
ON COMMIT PRESERVE ROWS) survives reconnects and is shared across sessions.

The build artifact is a PostgreSQL *server-side* loadable module
(``pgtt.so``) that a running postgres process dlopens at ``CREATE EXTENSION``
time, plus ``pgtt.control`` and the ``pgtt--*.sql`` install/upgrade scripts
(21 base versions + 20 upgrade steps).

Build system: PGXS (PostgreSQL Extension Building Infrastructure).  The
upstream Makefile does ``PG_CONFIG = pg_config`` /
``PGXS := $(shell $(PG_CONFIG) --pgxs)`` / ``include $(PGXS)`` and pgtt.c
hard-includes PostgreSQL *server* headers (``postgres.h``, ``access/*``,
``catalog/*``, ``executor/spi.h``, ``utils/*``, ``regex/regexport.h`` ...).
A plain libpq client install is not enough — the full server development tree
(``pg_config`` + PGXS makefiles + ``include/postgresql/server``) is required.

``postgresql/18.3`` is published in the ohpcd registry as a complete server +
client package (pg_config, PGXS, server headers, postgres/initdb/pg_ctl/
createdb/psql/pg_regress), so it is declared as a ``requires`` (build-time
headers + runtime host) instead of vendoring the PostgreSQL source tree: no
upstream PostgreSQL source is duplicated into this archive.  Upstream pgtt
requires PostgreSQL >= 12 (META.json prereqs); 18.3 satisfies it.

Design notes:
  R26: the package ships the loadable module ``pgtt.so`` only — no system
       library has that basename, so no static-link requirement applies.
  R32: the platform check accepts both Linux and OHOS.
  R33: no raw shell variables are used for the compiler; PGXS takes the
       compiler from its own ``pg_config --cc``.
  R34: test_package really loads the extension into a running PostgreSQL and
       executes SQL against it, plus the upstream pg_regress suite.
  R39: conandata.yml points at the official upstream GitHub tag archive.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PgttConan(ConanFile):
    name = "pgtt"
    version = "4.6"
    description = (
        "PostgreSQL extension implementing Oracle-style GLOBAL TEMPORARY "
        "TABLES (persistent definition, session-private data, ON COMMIT "
        "PRESERVE/DELETE ROWS)"
    )
    license = "PostgreSQL"
    homepage = "https://github.com/darold/pgtt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # The deliverable is a PostgreSQL loadable module (dlopen'ed by the
    # server), not a link library.
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    # A PostgreSQL extension module is dlopen-ed by the server; there is no
    # static-link form of the artifact.
    default_options = {"shared": True}

    # Upstream regression assets vendored into the package so test_package can
    # run the unmodified upstream suite against a live server.
    _UPSTREAM_TEST_DIRS = ("test/sql", "test/expected")

    def configure(self):
        # The OHOS profile declares settings.os.version=6.0, but neither the
        # build nor the package_id depends on it. Drop it so the package is not
        # held invalid by an undeclared setting value (same pattern as
        # archives/p/pgvector/0.8.6).
        self.settings.rm_safe("os.version")

    def validate(self):
        # R32: accept Linux and OHOS alike.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pgtt is only supported on Linux/OHOS, not {self.settings.os}")
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "pgtt is a PostgreSQL extension module and can only be built shared")

    def export_sources(self):
        # G1 gate requires the call site; it is a no-op when conandata.yml has
        # no `patches:` entries (pgtt 4.6 needs no source patch on OHOS).
        export_conandata_patches(self)

    def requirements(self):
        # PostgreSQL server headers + PGXS makefile + relocatable pg_config
        # (build) and the server that dlopens the module (runtime host).
        self.requires("postgresql/18.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # No patches are declared for 4.6 — upstream compiles unmodified on
        # OHOS — but the call is kept so adding a patch later needs no code
        # change. It is a no-op when conandata.yml has no `patches:` key.
        apply_conandata_patches(self)

    def _pg_config(self):
        """Absolute path of the pg_config provided by the postgresql requirement."""
        dep = self.dependencies["postgresql"]
        for bindir in dep.cpp_info.bindirs:
            candidate = os.path.join(bindir, "pg_config")
            if os.path.isfile(candidate):
                return candidate
        found = shutil.which("pg_config")
        if found:
            return found
        raise ConanException(
            "pg_config not found — the postgresql/18.3 dependency did not "
            "contribute its bin/ directory")

    def build(self):
        # PGXS resolves every path (server includes, CFLAGS, install dirs)
        # through pg_config at make time, and the packaged pg_config is
        # relocatable, so the build works wherever the conan cache lives.
        pg_config = self._pg_config()

        # rpathdir='$ORIGIN/../lib' replaces PGXS' default
        # `-Wl,-rpath,<pg_config --libdir>` with a *relocatable* RUNPATH: at
        # load time the module lives in `<prefix>/lib/postgresql`, so
        # $ORIGIN/../lib resolves to `<prefix>/lib`, where the server package
        # keeps libpq.so.5 (the module's only non-libc DT_NEEDED). The default
        # would bake the build machine's conan-cache path into the shipped
        # artifact (non-reproducible / L5 baseline churn).
        self.run(
            f'''make PG_CONFIG="{pg_config}" rpathdir='$$ORIGIN/../lib' -j1''',
            cwd=self.source_folder,
        )

    def package(self):
        # pgtt.so is the server module; pgtt.control relies on the default
        # module_pathname ($libdir/pgtt), so the shared object is deployed into
        # the PostgreSQL pkglibdir by the consumer.
        copy(self, "pgtt.so", self.source_folder,
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "pgtt.control", self.source_folder,
             os.path.join(self.package_folder, "share", "extension"))
        # 21 base install scripts (2.0.0 .. 4.6.0)
        copy(self, "pgtt--*.sql", os.path.join(self.source_folder, "sql"),
             os.path.join(self.package_folder, "share", "extension"))
        # 20 upgrade steps (2.0.0--2.1.0 .. 4.5.0--4.6.0)
        copy(self, "pgtt--*--*.sql", os.path.join(self.source_folder, "updates"),
             os.path.join(self.package_folder, "share", "extension"))
        # Vendor the upstream regression assets (test/sql + test/expected +
        # the standalone privilege test) so test_package can execute the
        # unmodified upstream suite against a live server.
        for rel in self._UPSTREAM_TEST_DIRS:
            copy(self, "*", os.path.join(self.source_folder, rel),
                 os.path.join(self.package_folder, "upstream", rel))
        copy(self, "privilege.sql", os.path.join(self.source_folder, "test"),
             os.path.join(self.package_folder, "upstream", "test"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # pgtt.so is a PostgreSQL loadable module (dlopen'ed by the server
        # through $libdir/pgtt), not a link library — it carries no SONAME and
        # leaves the PostgreSQL server symbols undefined on purpose. The
        # cpp_info entry follows the convention of the other PostgreSQL
        # extension recipes in this repository; the real consumer interface is
        # "copy lib/pgtt.so into $(pg_config --pkglibdir) and
        # share/extension/* into $(pg_config --sharedir)/extension".
        self.cpp_info.libs = ["pgtt"]
        self.cpp_info.libdirs = ["lib"]
        # share/extension holds pgtt.control and the pgtt--*.sql scripts that a
        # PostgreSQL deployment copies into its sharedir.
        self.cpp_info.resdirs = ["share"]
