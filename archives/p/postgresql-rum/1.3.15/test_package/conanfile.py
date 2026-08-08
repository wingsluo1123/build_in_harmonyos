import os
import subprocess

from conan import ConanFile


class TestPostgresqlRumConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Verify rum.so exists and exports the extension entry symbol
        pkg_folder = self.dependencies["postgresql-rum"].package_folder
        rum_so = os.path.join(pkg_folder, "lib", "rum.so")
        assert os.path.isfile(rum_so), f"rum.so not found at {rum_so}"
        # Verify _PG_init symbol is exported (R34: real API verification)
        result = subprocess.run(["nm", "-D", rum_so], capture_output=True, text=True)
        assert "_PG_init" in result.stdout, f"_PG_init not found in rum.so"
        # Verify pg_config from PostgreSQL dependency exists
        pg_folder = self.dependencies["postgresql"].package_folder
        pg_config = os.path.join(pg_folder, "bin", "pg_config")
        assert os.path.isfile(pg_config), f"pg_config not found at {pg_config}"
