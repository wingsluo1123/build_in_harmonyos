#!/usr/bin/env python3
"""Conan recipe — postgresql-topn 2.7.0 (Makefile/PGXS)"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PostgresqlTopnConan(ConanFile):
    name = "postgresql-topn"
    version = "2.7.0"
    description = "PostgreSQL extension for fast top-N queries using approximate algorithm"
    license = "PostgreSQL"
    homepage = "https://github.com/citusdata/postgresql-topn"
    url = ""

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_pg_config(self):
        """Find pg_config binary in PATH."""
        pg_config = shutil.which("pg_config")
        if pg_config is None:
            for candidate in [
                os.path.expanduser("~/usr/local/bin/pg_config"),
                "/usr/local/bin/pg_config",
            ]:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    pg_config = candidate
                    break
        if pg_config is None:
            raise ConanInvalidConfiguration(
                "pg_config not found. PostgreSQL must be installed to build postgresql-topn. "
                "Install PostgreSQL to $HOME/usr/local or ensure pg_config is in PATH."
            )
        return pg_config

    def build(self):
        apply_conandata_patches(self)

        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("postgresql-topn only supports Linux/OHOS")

        pg_config = self._find_pg_config()

        # PGXS needs cpp (C preprocessor) for SQL file generation.
        # On OHOS, clang-cpp is available at /data/service/hnp/bin/clang-cpp.
        # Create a 'cpp' wrapper in a temp bin dir so the Makefile's default SQLPP works.
        bin_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        cpp_link = os.path.join(bin_dir, "cpp")
        clang_cpp = "/data/service/hnp/bin/clang-cpp"
        if os.path.isfile(clang_cpp) and not shutil.which("cpp"):
            if os.path.lexists(cpp_link):
                os.remove(cpp_link)
            os.symlink(clang_cpp, cpp_link)

        # Build PATH to include our bin dir
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = bin_dir + ":" + old_path

        try:
            # Build using PGXS (make with pg_config)
            self.run(f'make PG_CONFIG="{pg_config}" -j1', cwd=self.source_folder)

            # Install to staging directory
            staging = os.path.join(self.build_folder, "staging")
            os.makedirs(staging, exist_ok=True)
            self.run(
                f'make install PG_CONFIG="{pg_config}" DESTDIR="{staging}"',
                cwd=self.source_folder,
            )
        finally:
            os.environ["PATH"] = old_path

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        if not os.path.isdir(staging):
            return

        # Walk staging and copy lib/ and share/ contents
        for root, dirs, files in os.walk(staging):
            for f in files:
                src = os.path.join(root, f)
                rel = os.path.relpath(src, staging)
                parts = rel.split(os.sep)
                for i, part in enumerate(parts):
                    if part in ("lib", "share"):
                        dest_rel = os.path.join(*parts[i:])
                        dest = os.path.join(self.package_folder, dest_rel)
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        shutil.copy2(src, dest)
                        break

    def package_info(self):
        self.cpp_info.libs = ["topn"]
        self.cpp_info.libdirs = ["lib/postgresql"]
