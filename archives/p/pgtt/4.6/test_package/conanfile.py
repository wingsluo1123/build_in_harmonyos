import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException


class PgttTestConan(ConanFile):
    """Consumer test for the pgtt package.

    The heavy lifting lives in ``pgtt_test.py`` (artifact assertions on the
    packaged ``pgtt.so``, consumer SQL against a real PostgreSQL server, and
    the upstream pg_regress suite).  This file is the Conan driver entry point;
    the ``self.run()`` call is what CI's L0d gate checks.
    """

    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # The PostgreSQL *server* binaries (initdb / postgres / pg_ctl / psql /
        # pg_regress) used to boot the throw-away cluster for the functional and
        # regression checks.  pgtt itself only needs the server headers + PGXS
        # at build time; here we need a runnable server.
        self.tool_requires("postgresql/18.3")

    def _postgres_bindir(self):
        """Directory holding the postgresql package's pg_config/postgres."""
        for accessor in (self.dependencies, self.dependencies.build):
            try:
                dep = accessor["postgresql"]
            except Exception:                                      # noqa: BLE001
                continue
            for bindir in dep.cpp_info.bindirs:
                if os.path.isfile(os.path.join(bindir, "pg_config")):
                    return bindir
        found = shutil.which("pg_config")
        return os.path.dirname(found) if found else ""

    def test(self):
        dep = self.dependencies["pgtt"]
        pkg = dep.package_folder
        if not pkg:
            raise ConanException("pgtt package folder not populated")

        harness = os.path.join(self.source_folder, "pgtt_test.py")
        if not os.path.isfile(harness):
            raise ConanException("test driver not found: %s" % harness)

        cmd = [sys.executable, harness, "--package", pkg]
        bindir = self._postgres_bindir()
        if bindir:
            cmd += ["--pg-bindir", bindir]

        self.output.info("pgtt consumer harness: " + " ".join(cmd))
        self.run(" ".join(shlex.quote(part) for part in cmd), env="conanbuild")
