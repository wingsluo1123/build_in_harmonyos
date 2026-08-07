import os

from conan import ConanFile


class TestPostgresqlConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Conan 2.x: use conanrun env which sets PATH to include package bin/
        self.run("pg_config --version", env="conanrun")
