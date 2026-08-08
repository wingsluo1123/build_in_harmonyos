import os
import subprocess

from conan import ConanFile


class QtUnixodbcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["qt-unixodbc"]
        qt5 = self.dependencies["qt5-qtbase"]

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp") or compilers.get("cxx") or "clang++"

        inc_dir = os.path.join(dep.package_folder, "include")
        qt5_inc = os.path.join(qt5.package_folder, "include")
        qt5_lib = os.path.join(qt5.package_folder, "lib")
        dep_lib = os.path.join(dep.package_folder, "lib")

        src_file = os.path.join(self.source_folder, "test.cpp")
        out_bin = os.path.join(self.build_folder, "test_qt_unixodbc")

        cmd = (
            f'{cxx} -std=c++14 -O2 -fPIC '
            f'-I{inc_dir} -I{inc_dir}/QtSql '
            f'-I{qt5_inc} -I{qt5_inc}/QtCore '
            f'{src_file} -o {out_bin} '
            f'-L{dep_lib} -lQt5Sql '
            f'-L{qt5_lib} -lQt5Core '
            f'-Wl,-rpath,{dep_lib} -Wl,-rpath,{qt5_lib}'
        )
        self.run(cmd)

    def test(self):
        dep = self.dependencies["qt-unixodbc"]
        qt5 = self.dependencies["qt5-qtbase"]
        dep_lib = os.path.join(dep.package_folder, "lib")
        qt5_lib = os.path.join(qt5.package_folder, "lib")

        library_paths = [dep_lib, qt5_lib, os.environ.get("LD_LIBRARY_PATH")]
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            path for path in library_paths if path
        )

        test_bin = os.path.join(self.build_folder, "test_qt_unixodbc")
        self.run(test_bin, ignore_errors=False)

        # Verify the ODBC driver plugin exists
        plugin_dir = os.path.join(dep.package_folder, "plugins", "sqldrivers")
        so_path = os.path.join(plugin_dir, "libqsqlodbc.so")
        assert os.path.isfile(so_path), f"libqsqlodbc.so not found at {so_path}"
