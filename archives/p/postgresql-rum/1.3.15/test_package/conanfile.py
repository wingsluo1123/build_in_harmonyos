import os

from conan import ConanFile


class TestPostgresqlRumConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Verify rum.so exists and exports the extension entry symbol
        # conanrun env sets LD_LIBRARY_PATH to include postgresql-rum's libdirs
        self.run(
            'for d in $(echo $LD_LIBRARY_PATH | tr ":" " "); do '
            'if [ -f "$d/rum.so" ]; then '
            '  echo "rum.so found in $d"; '
            '  nm -D "$d/rum.so" 2>/dev/null | grep -q " _PG_init" '
            '    && echo "_PG_init symbol verified" && exit 0; '
            '  echo "ERROR: _PG_init not found" && exit 1; '
            'fi; done; echo "rum.so NOT found" && exit 1',
            env="conanrun",
        )
        # Verify pg_config from PostgreSQL dependency
        self.run("pg_config --version", env="conanrun")
