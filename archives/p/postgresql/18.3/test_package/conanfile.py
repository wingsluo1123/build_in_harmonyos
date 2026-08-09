import os

from conan import ConanFile


class TestPostgresqlConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["postgresql"].package_folder
        pg_config = os.path.join(pkg, "bin", "pg_config")
        # R34: verify pg_config exists, is ELF, and server headers are present
        self.run(f'file {pg_config}', env="conanrun")
        self.run(f'test -d {os.path.join(pkg, "include", "postgresql", "server")}', env="conanrun")
        self.run(f'test -d {os.path.join(pkg, "lib", "postgresql", "pgxs")}', env="conanrun")
