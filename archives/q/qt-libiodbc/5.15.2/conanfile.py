import os
import shlex
import subprocess
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.layout import basic_layout


class QtLibiodbcConan(ConanFile):
    name = "qt-libiodbc"
    version = "5.15.2"
    description = "Qt5 iODBC SQL driver plugin (QIODBCDriver)"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        pass

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2")
        self.requires("libiodbc/3.52.16")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qt-libiodbc only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        src_dir = self.source_folder
        build_dir = self.build_folder
        os.makedirs(build_dir, exist_ok=True)

        # Get dependency paths
        qt5 = self.dependencies["qt5-qtbase"]
        qt5_dir = qt5.package_folder
        iodbc = self.dependencies["libiodbc"]
        iodbc_dir = iodbc.package_folder

        qt5_inc = os.path.join(qt5_dir, "include")
        qt5_lib = os.path.join(qt5_dir, "lib")
        qt5_bin = os.path.join(qt5_dir, "bin")
        qt5_src = os.path.join(qt5_dir, "src")

        iodbc_inc = os.path.join(iodbc_dir, "include")
        iodbc_lib = os.path.join(iodbc_dir, "lib")

        # Create QtSql config headers (qt5-qtbase built with -no-feature-sql)
        extra_inc = os.path.join(build_dir, "extra_includes")
        qtsql_inc = os.path.join(extra_inc, "QtSql")
        qtsql_private_inc = os.path.join(qtsql_inc, "private")
        os.makedirs(qtsql_private_inc, exist_ok=True)
        for hdr in ("qtsql-config.h", "qtsql-config_p.h"):
            src_hdr = os.path.join(qt5_src, "sql", hdr)
            if os.path.isfile(src_hdr):
                shutil.copy2(src_hdr, os.path.join(qtsql_inc, hdr))
                shutil.copy2(src_hdr, os.path.join(qtsql_private_inc, hdr))

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")

        # 1. Patch ODBC driver source for iODBC
        self._patch_odbc_driver(src_dir)

        # 3. Run moc on main.cpp and copy to source dir for #include "main.moc"
        moc = os.path.join(qt5_bin, "moc")
        odbc_src = os.path.join(src_dir, "src", "plugins", "sqldrivers", "odbc")
        moc_output = os.path.join(odbc_src, "main.moc")
        self.run(
            f'{shlex.quote(moc)} -DQT_PLUGIN -DQT_SQL_LIB -DQT_CORE_LIB '
            f'-I{shlex.quote(qt5_inc)} '
            f'-I{shlex.quote(os.path.join(qt5_inc, "QtCore"))} '
            f'-I{shlex.quote(os.path.join(qt5_inc, "QtSql"))} '
            f'-o {shlex.quote(moc_output)} '
            f'{shlex.quote(os.path.join(odbc_src, "main.cpp"))}',
            env="conanbuild",
        )

        # 3. Compile ODBC driver source files
        cxxflags = (
            "-pipe -O2 -std=c++14 -Wall -Wextra -Wno-deprecated-declarations "
            "-D_REENTRANT -fPIC "
            "-DQT_NO_CAST_TO_ASCII -DQT_NO_CAST_FROM_ASCII -DQT_NO_DEBUG "
            "-DQT_PLUGIN -DQT_SQL_LIB -DQT_CORE_LIB "
            "-DUNICODE"
        )

        # Include paths: qt5-qtbase headers + iodbc headers + odbc source + extra QtSql config
        includes = (
            f'-I{shlex.quote(odbc_src)} '
            f'-I{shlex.quote(qt5_inc)} '
            f'-I{shlex.quote(os.path.join(qt5_inc, "QtCore"))} '
            f'-I{shlex.quote(os.path.join(qt5_inc, "QtSql"))} '
            f'-I{shlex.quote(os.path.join(qt5_inc, "QtCore", "5.15.2"))} '
            f'-I{shlex.quote(os.path.join(qt5_inc, "QtCore", "5.15.2", "QtCore"))} '
            f'-I{shlex.quote(os.path.join(qt5_inc, "QtSql", "5.15.2"))} '
            f'-I{shlex.quote(os.path.join(qt5_inc, "QtSql", "5.15.2", "QtSql"))} '
            f'-I{shlex.quote(extra_inc)} '
            f'-I{shlex.quote(os.path.join(qt5_src, "corelib"))} '
            f'-I{shlex.quote(iodbc_inc)} '
            f'-I{shlex.quote(os.path.join(qt5_dir, "mkspecs", "linux-clang"))}'
        )

        # Compile qsql_odbc.cpp
        self.run(
            f'{shlex.quote(cxx)} -c {cxxflags} {includes} '
            f'-o {shlex.quote(os.path.join(build_dir, "qsql_odbc.o"))} '
            f'{shlex.quote(os.path.join(odbc_src, "qsql_odbc.cpp"))}',
            env="conanbuild",
        )

        # Compile main.cpp
        self.run(
            f'{shlex.quote(cxx)} -c {cxxflags} {includes} '
            f'-o {shlex.quote(os.path.join(build_dir, "main.o"))} '
            f'{shlex.quote(os.path.join(odbc_src, "main.cpp"))}',
            env="conanbuild",
        )

        # 5. Link the driver plugin
        # The driver links against Qt5Sql, Qt5Core, and libiodbc
        # Qt5Sql is not in the conan package (built with -no-feature-sql)
        # but Qt5Core is. The driver plugin is a .so that gets dlopen'd
        # at runtime, so we use --allow-undefined-symbols for the
        # Qt5Sql symbols (resolved at runtime by the Qt5 SQL module).
        libs = (
            f'-L{shlex.quote(qt5_lib)} '
            f'-L{shlex.quote(iodbc_lib)} '
            f'-lQt5Core -liodbc -liodbcinst '
            f'-Wl,-soname,libqsqliodbc.so'
        )
        self.run(
            f'{shlex.quote(cxx)} -shared -o '
            f'{shlex.quote(os.path.join(build_dir, "libqsqliodbc.so"))} '
            f'{shlex.quote(os.path.join(build_dir, "qsql_odbc.o"))} '
            f'{shlex.quote(os.path.join(build_dir, "main.o"))} '
            f'{libs}',
            env="conanbuild",
        )

    def _patch_odbc_driver(self, src_dir):
        """Modify ODBC driver source to use iODBC driver keys and fix compat."""
        odbc_src = os.path.join(src_dir, "src", "plugins", "sqldrivers", "odbc")
        main_cpp = os.path.join(odbc_src, "main.cpp")
        if os.path.isfile(main_cpp):
            with open(main_cpp, "r") as f:
                content = f.read()
            content = content.replace('"QODBC3"', '"QIODBC3"')
            content = content.replace('"QODBC"', '"QIODBC"')
            with open(main_cpp, "w") as f:
                f.write(content)

        # Fix QChar private constructor issue (Qt 5.15 compat)
        odbc_cpp = os.path.join(odbc_src, "qsql_odbc.cpp")
        if os.path.isfile(odbc_cpp):
            with open(odbc_cpp, "r") as f:
                content = f.read()
            content = content.replace(
                "quote = QChar(driverResponse[0]);",
                "quote = QChar::fromLatin1(driverResponse[0]);",
            )
            with open(odbc_cpp, "w") as f:
                f.write(content)

    def package(self):
        build_dir = self.build_folder
        # Copy the driver plugin to sqldrivers/
        sqldrivers_dir = os.path.join(self.package_folder, "sqldrivers")
        os.makedirs(sqldrivers_dir, exist_ok=True)
        driver = os.path.join(build_dir, "libqsqliodbc.so")
        if os.path.isfile(driver):
            shutil.copy2(driver, os.path.join(sqldrivers_dir, "libqsqliodbc.so"))

    def package_info(self):
        self.cpp_info.libs = ["qsqliodbc"]
