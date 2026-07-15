import os

from conan import ConanFile
from conan.tools.files import get, copy, patch
from conan.tools.layout import basic_layout


class LibpgqueryConan(ConanFile):
    name = "libpg_query"
    version = "18.0.0"
    description = "C library for accessing the PostgreSQL parser outside of the server environment"
    license = "MIT"
    homepage = "https://github.com/pganalyze/libpg_query"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*.patch"

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        # Apply patches from conandata.yml
        patches = self.conan_data.get("patches", [])
        if isinstance(patches, dict):
            patch_list = patches.values()
        else:
            patch_list = patches
        for p in patch_list:
            if isinstance(p, dict):
                pf = p.get("patch_file", "")
                paths = [
                    os.path.join(self.export_sources_folder, pf) if hasattr(self, 'export_sources_folder') else "",
                    os.path.join(self.source_folder, pf),
                ]
                for path in paths:
                    if path and os.path.exists(path):
                        patch(self, patch_file=path)
                        break

        # libpg_query uses a plain Makefile, not autotools
        # "make build" only compiles the static library, avoiding linker issues
        self.run("make build -j1", cwd=self.source_folder)

    def package(self):
        # No "make install" target; manually copy artifacts
        src = self.source_folder
        copy(self, "libpg_query.a", src=src, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "pg_query.h", src=src, dst=os.path.join(self.package_folder, "include"))
        copy(self, "postgres_deparse.h", src=src, dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["pg_query"]
