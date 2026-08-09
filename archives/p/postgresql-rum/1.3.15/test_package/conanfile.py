import os

from conan import ConanFile


class TestPostgresqlRumConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Verify rum.so exists and exports the extension entry symbol
        rum = self.dependencies["postgresql-rum"].package_folder
        rum_so = os.path.join(rum, "lib", "rum.so")
        # Verify rum.so exists and exports _PG_init
        self.run(f'nm -D {rum_so} | grep _PG_init', env="conanrun")
        # Verify pg_config from PostgreSQL dependency
        pg = self.dependencies["postgresql"].package_folder
        pg_config = os.path.join(pg, "bin", "pg_config")
        self.run(f'file {pg_config}', env="conanrun")
