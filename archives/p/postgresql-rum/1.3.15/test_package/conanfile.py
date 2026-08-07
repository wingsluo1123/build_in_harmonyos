import os

from conan import ConanFile


class TestPostgresqlRumConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify rum.so exists in the package lib directory
        # conanrun env sets LD_LIBRARY_PATH to include postgresql-rum's libdirs
        self.run(
            'for d in $(echo $LD_LIBRARY_PATH | tr ":" " "); do '
            'test -f "$d/rum.so" && echo "rum.so found in $d" && exit 0; '
            'done; echo "rum.so NOT found" && exit 1',
            env="conanrun",
        )
        # Verify pg_config from PostgreSQL dependency
        self.run("pg_config --version", env="conanrun")
