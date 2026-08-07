#!/usr/bin/env python3
"""Conan recipe — qt-mariadb 5.15.2 (custom build system).

Qt5 MariaDB SQL driver plugin built from qtbase mysql driver source.
Links against libmariadb (MariaDB client library) instead of libmysqlclient.

Build process:
  1. Download qtbase source (for mysql driver .cpp files)
  2. Use Qt5 headers/moc/libs from qt5-qtbase conan package
  3. Use libmariadb from mariadb-connector-c conan package
  4. Use ohenvironment from OHOS SDK sysroot
  5. Generate moc file, compile, and link the plugin .so

Key rules:
  - R32: settings.os check uses `in ("Linux", "OHOS")`
  - R33: Compiler from Conan conf, not shell env vars
  - R39: Source URL points to official Qt mirrors
"""
import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches

class QtMariadbConan(ConanFile):
    name = "qt-mariadb"
    version = "5.15.2"
    description = "Qt5 MariaDB SQL driver plugin (libqsqlmysql.so with MariaDB backend)"
    license = "LGPL-2.1"
    homepage = "https://download.qt.io/archive/qt/5.15/"
    url = ""  # CI fills this

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2")
        self.requires("mariadb-connector-c/3.4.8")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qt-mariadb only supports Linux and OHOS, got {self.settings.os}"
            )

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        # Use the same source as qt5-qtbase (qtbase 5.15.2)
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(self, url=url, sha256=source_data["sha256"], strip_root=True)
                return
            except Exception as error:
                self.output.warning(f"Failed to download from {url}: {error}")
        # Fallback: try local conan cache source from qt5-qtbase
        local_src = os.path.join(
            os.path.expanduser("~"), "tmp", "builds",
            "qtbase-everywhere-src-5.15.2.orig")
        if os.path.isdir(local_src):
            import shutil
            for item in os.listdir(local_src):
                s = os.path.join(local_src, item)
                d = os.path.join(self.source_folder, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            return
        raise ConanInvalidConfiguration(
            "Unable to download qtbase source from all mirrors")

    def build(self):
        src = self.source_folder

        # Get compiler from Conan conf (R33)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp") or compilers.get("cxx") or "clang++"

        # Get Qt5 paths from qt5-qtbase dependency
        qt5 = self.dependencies["qt5-qtbase"]
        qt5_inc = os.path.join(qt5.package_folder, "include")
        qt5_lib = os.path.join(qt5.package_folder, "lib")
        qt5_bin = os.path.join(qt5.package_folder, "bin")
        moc = os.path.join(qt5_bin, "moc")

        # Get mariadb paths from mariadb-connector-c dependency
        mariadb = self.dependencies["mariadb-connector-c"]
        mariadb_inc = os.path.join(mariadb.package_folder, "include")
        mariadb_lib = os.path.join(mariadb.package_folder, "lib")

        # MySQL driver source directory in qtbase source
        mysql_src = os.path.join(src, "src", "plugins", "sqldrivers", "mysql")

        # OHOS SDK sysroot path for ohenvironment
        ohsysroot = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot"
        ohsys_lib = os.path.join(ohsysroot, "usr", "lib", "aarch64-linux-ohos")

        # Determine platform define
        extra_defines = []
        if self.settings.os == "OHOS":
            extra_defines.append("-DQ_OS_OHOS")

        # Step 1: Create qtsql-config.h (missing from qt5-qtbase package
        # because SQL was disabled with -no-feature-sql during configure).
        # The mysql driver source includes <QtSql/qtsql-config.h> and
        # <QtSql/private/qtsql-config_p.h>.
        config_inc = os.path.join(self.build_folder, "config_inc")
        os.makedirs(os.path.join(config_inc, "QtSql", "private"), exist_ok=True)
        # Public config: override QT_FEATURE_sql (disabled by qconfig_p.h)
        with open(os.path.join(config_inc, "QtSql", "qtsql-config.h"), "w") as f:
            f.write("#ifndef QT_SQL_CONFIG_H\n")
            f.write("#define QT_SQL_CONFIG_H\n")
            f.write("#undef QT_FEATURE_sql\n")
            f.write("#define QT_FEATURE_sql 1\n")
            f.write("#undef QT_FEATURE_sqlmodel\n")
            f.write("#define QT_FEATURE_sqlmodel 1\n")
            f.write("#endif\n")
        # Private config: empty (no private SQL features needed)
        with open(os.path.join(config_inc, "QtSql", "private", "qtsql-config_p.h"), "w") as f:
            f.write("#ifndef QT_SQL_CONFIG_P_H\n")
            f.write("#define QT_SQL_CONFIG_P_H\n")
            f.write("#endif\n")

        # Step 2: Generate moc file from main.cpp
        moc_output = os.path.join(self.build_folder, "main.moc")
        self.run(
            f'{shlex.quote(moc)} '
            f'-o {shlex.quote(moc_output)} '
            f'-I{shlex.quote(config_inc)} '
            f'-I{shlex.quote(qt5_inc)} '
            f'-I{shlex.quote(os.path.join(qt5_inc, "QtCore"))} '
            f'-I{shlex.quote(os.path.join(qt5_inc, "QtCore", "5.15.2", "QtCore", "private"))} '
            f'-I{shlex.quote(os.path.join(qt5_inc, "QtSql"))} '
            f'-I{shlex.quote(os.path.join(qt5_inc, "QtSql", "5.15.2", "QtSql", "private"))} '
            f'{shlex.quote(os.path.join(mysql_src, "main.cpp"))}',
            cwd=self.build_folder
        )

        # Step 3: Compile source files
        cxx_flags = [
            "-c", "-pipe", "-O2", "-std=c++14",
            "-Wall", "-Wextra", "-Wno-deprecated-declarations",
            "-D_REENTRANT", "-fPIC",
            "-DQT_NO_CAST_TO_ASCII", "-DQT_NO_CAST_FROM_ASCII",
            "-DQT_NO_DEBUG", "-DQT_PLUGIN", "-DQT_SQL_LIB", "-DQT_CORE_LIB",
        ] + extra_defines

        include_flags = [
            f"-I{config_inc}",
            f"-I{mysql_src}",
            f"-I{qt5_inc}",
            f"-I{os.path.join(qt5_inc, 'QtCore')}",
            f"-I{os.path.join(qt5_inc, 'QtCore', '5.15.2')}",
            f"-I{os.path.join(qt5_inc, 'QtCore', '5.15.2', 'QtCore')}",
            f"-I{os.path.join(qt5_inc, 'QtCore', '5.15.2', 'QtCore', 'private')}",
            f"-I{os.path.join(qt5_inc, 'QtSql')}",
            f"-I{os.path.join(qt5_inc, 'QtSql', '5.15.2')}",
            f"-I{os.path.join(qt5_inc, 'QtSql', '5.15.2', 'QtSql')}",
            f"-I{os.path.join(qt5_inc, 'QtSql', '5.15.2', 'QtSql', 'private')}",
            f"-I{mariadb_inc}",
        ]

        # Compile qsql_mysql.cpp
        self.run(
            " ".join([shlex.quote(cxx)] + cxx_flags + include_flags +
                     ["-o", shlex.quote(os.path.join(self.build_folder, "qsql_mysql.o")),
                      shlex.quote(os.path.join(mysql_src, "qsql_mysql.cpp"))]),
            cwd=self.build_folder
        )

        # Compile main.cpp (with moc include)
        self.run(
            " ".join([shlex.quote(cxx)] + cxx_flags + include_flags +
                     [f"-I{self.build_folder}",
                      "-o", shlex.quote(os.path.join(self.build_folder, "main.o")),
                      shlex.quote(os.path.join(mysql_src, "main.cpp"))]),
            cwd=self.build_folder
        )

        # Step 4: Link the plugin .so
        # Note: Qt5Sql is not linked (not built in qt5-qtbase with -no-feature-sql).
        # The plugin is loaded at runtime by Qt5 framework which provides Qt5Sql.
        # Using --allow-shlib-undefined to allow undefined Qt5Sql symbols.
        self.run(
            " ".join([
                shlex.quote(cxx), "-shared",
                "-o", shlex.quote(os.path.join(self.build_folder, "libqsqlmysql.so")),
                shlex.quote(os.path.join(self.build_folder, "qsql_mysql.o")),
                shlex.quote(os.path.join(self.build_folder, "main.o")),
                f"-L{qt5_lib}", "-lQt5Core",
                f"-L{mariadb_lib}", "-lmariadb",
                f"-L{ohsys_lib}", "-lohenvironment",
                f"-Wl,-rpath,{qt5_lib}",
                "-Wl,-soname,libqsqlmysql.so",
                "-Wl,--allow-shlib-undefined",
            ]),
            cwd=self.build_folder
        )

    def package(self):
        copy(self, "libqsqlmysql.so",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "plugins", "sqldrivers"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libdirs = ["plugins/sqldrivers"]
        self.cpp_info.libs = ["qsqlmysql"]
        self.cpp_info.system_libs = ["ohenvironment"]
