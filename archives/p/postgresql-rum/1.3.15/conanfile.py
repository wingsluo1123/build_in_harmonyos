import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class PostgresqlRumConan(ConanFile):
    name = "postgresql-rum"
    version = "1.3.15"
    description = "RUM index access method for PostgreSQL - faster full-text search with positional information"
    license = "PostgreSQL"
    homepage = "https://github.com/postgrespro/rum"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("postgresql/18.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Get pg_config from PostgreSQL dependency
        pg_config = os.path.join(
            self.dependencies["postgresql"].package_folder, "bin", "pg_config"
        )
        # Build using PGXS (PostgreSQL Extension Build System)
        # Run make in source folder where Makefile is located
        # R9: use -j1
        # R33: PGXS uses pg_config to get CC/CFLAGS, no shell env dependency
        self.run(
            f'make USE_PGXS=1 PG_CONFIG="{pg_config}" -j1',
            env="conanbuild",
            cwd=self.source_folder,
        )
        # L1: Run upstream tests (requires PostgreSQL server, may fail on OHOS)
        try:
            self.run(
                f'make USE_PGXS=1 PG_CONFIG="{pg_config}" installcheck',
                env="conanbuild",
                cwd=self.source_folder,
            )
        except Exception as e:
            self.output.warning(f"make installcheck failed (expected on OHOS): {e}")

    def package(self):
        # Copy the built shared library (built in source folder by PGXS)
        copy(self, "rum.so", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        # Copy extension SQL and control files
        copy(self, "rum.control", self.source_folder,
             os.path.join(self.package_folder, "share", "extension"))
        copy(self, "rum--*.sql", self.source_folder,
             os.path.join(self.package_folder, "share", "extension"))
        # Copy header files
        copy(self, "rum.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "rumsort.h", self.source_folder,
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["rum"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # Extension data files (SQL, control) are in share/extension/
        self.cpp_info.resdirs = ["share"]
