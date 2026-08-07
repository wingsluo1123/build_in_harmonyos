import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import export_conandata_patches, get, copy as conan_copy
from conan.errors import ConanInvalidConfiguration


class QtMysqlConan(ConanFile):
    name = "qt-mysql"
    version = "5.15.2"
    description = "Qt5 MySQL/MariaDB SQL driver plugin (QMYSQLDriver)"
    license = "LGPL-2.1"
    homepage = "https://download.qt.io/archive/qt/5.15/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2")
        self.requires("mariadb-connector-c/3.4.8")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("qt-mysql is only supported on Linux/OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        src_dir = self.source_folder
        # Check if source was extracted; if not, re-download
        mysql_src = os.path.join(src_dir, "src", "plugins", "sqldrivers", "mysql", "qsql_mysql.cpp")
        if not os.path.exists(mysql_src):
            get(self, **self.conan_data["sources"], strip_root=True, destination=src_dir)

        # Apply patch manually if not already applied
        for patch_info in self.conan_data.get("patches", []):
            patch_file = patch_info.get("patch_file", "")
            if patch_file:
                patch_path = os.path.join(src_dir, patch_file)
                if os.path.exists(patch_path):
                    self.run(f'cd "{src_dir}" && patch -p1 --forward < "{patch_path}" || true')
                    self.output.info(f"Applied patch: {patch_file}")

        self._build_qt5sql()
        self._build_mysql_plugin()

    def _get_qt5_info(self):
        qt5 = self.dependencies["qt5-qtbase"]
        return qt5.package_folder

    def _get_mariadb_info(self):
        maria = self.dependencies["mariadb-connector-c"]
        return maria.package_folder

    def _create_forward_headers(self, qt5_pkg, tmpinc):
        os.makedirs(os.path.join(tmpinc, "QtSql", "private"), exist_ok=True)
        os.makedirs(os.path.join(tmpinc, "QtCore", "private"), exist_ok=True)

        config_path = os.path.join(qt5_pkg, "src", "sql", "qtsql-config.h")
        if os.path.exists(config_path):
            with open(os.path.join(tmpinc, "QtSql", "qtsql-config.h"), "w") as f:
                f.write(f'#include "{config_path}"\n')

        config_p_path = os.path.join(qt5_pkg, "src", "sql", "qtsql-config_p.h")
        if os.path.exists(config_p_path):
            with open(os.path.join(tmpinc, "QtSql", "private", "qtsql-config_p.h"), "w") as f:
                f.write(f'#include "{config_p_path}"\n')

        sql_priv_dir = os.path.join(qt5_pkg, "include", "QtSql", "5.15.2", "QtSql", "private")
        if os.path.isdir(sql_priv_dir):
            for h in os.listdir(sql_priv_dir):
                src = os.path.join(sql_priv_dir, h)
                with open(os.path.join(tmpinc, "QtSql", "private", h), "w") as f:
                    f.write(f'#include "{src}"\n')

        core_priv_dir = os.path.join(qt5_pkg, "include", "QtCore", "5.15.2", "QtCore", "private")
        if os.path.isdir(core_priv_dir):
            for h in os.listdir(core_priv_dir):
                src = os.path.join(core_priv_dir, h)
                with open(os.path.join(tmpinc, "QtCore", "private", h), "w") as f:
                    f.write(f'#include "{src}"\n')

    def _build_qt5sql(self):
        qt5_pkg = self._get_qt5_info()
        src_dir = self.source_folder
        sql_src = os.path.join(src_dir, "src", "sql")
        build_dir = os.path.join(self.build_folder, "qt5sql_build")
        tmpinc = os.path.join(self.build_folder, "forward_headers")
        moc_dir = os.path.join(build_dir, "moc")
        os.makedirs(moc_dir, exist_ok=True)

        self._create_forward_headers(qt5_pkg, tmpinc)

        includes = " ".join([
            f"-I{tmpinc}",
            f"-I{qt5_pkg}/include",
            f"-I{qt5_pkg}/include/QtCore",
            f"-I{qt5_pkg}/include/QtCore/5.15.2/QtCore/private",
            f"-I{qt5_pkg}/include/QtCore/5.15.2/QtCore",
            f"-I{qt5_pkg}/include/QtSql",
            f"-I{qt5_pkg}/include/QtSql/5.15.2/QtSql/private",
            f"-I{qt5_pkg}/include/QtSql/5.15.2/QtSql",
            f"-I{tmpinc}/QtSql",
            f"-I{qt5_pkg}/src/sql",
            f"-I{sql_src}/kernel",
            f"-I{sql_src}/models",
            f"-I{qt5_pkg}/src/corelib",
            f"-I{qt5_pkg}/src/corelib/global",
            f"-I{qt5_pkg}/src/corelib/kernel",
            f"-I{qt5_pkg}/src/corelib/tools",
            f"-I{qt5_pkg}/src/corelib/serialization",
            f"-I{qt5_pkg}/src/corelib/text",
            f"-I{qt5_pkg}/src/corelib/io",
            f"-I{qt5_pkg}/src/corelib/itemmodels",
            f"-I{qt5_pkg}/src/corelib/plugin",
            f"-I{qt5_pkg}/mkspecs/linux-clang",
        ])

        cflags = (
            "-pipe -O2 -std=c++14 -Wall -Wextra -fPIC "
            "-D_REENTRANT -DQT_NO_USING_NAMESPACE "
            "-DQT_NO_CAST_FROM_ASCII -DQT_NO_CAST_TO_ASCII -DQT_NO_FOREACH "
            "-DQT_BUILD_SQL_LIB -DQT_CORE_LIB -DQT_NO_DEBUG"
        )

        moc = os.path.join(qt5_pkg, "bin", "moc")

        moc_headers = [
            "kernel/qsqldriver.h",
            "kernel/qsqldriverplugin.h",
            "models/qsqlquerymodel.h",
            "models/qsqlrelationaltablemodel.h",
            "models/qsqltablemodel.h",
        ]
        for h in moc_headers:
            self.run(f'{moc} {os.path.join(sql_src, h)} -o {os.path.join(moc_dir, "moc_" + os.path.basename(h))}')

        kernel_sources = [
            "kernel/qsqlcachedresult.cpp", "kernel/qsqldatabase.cpp",
            "kernel/qsqldriver.cpp", "kernel/qsqldriverplugin.cpp",
            "kernel/qsqlerror.cpp", "kernel/qsqlfield.cpp",
            "kernel/qsqlindex.cpp", "kernel/qsqlquery.cpp",
            "kernel/qsqlrecord.cpp", "kernel/qsqlresult.cpp",
        ]
        model_sources = [
            "models/qsqlquerymodel.cpp", "models/qsqlrelationaldelegate.cpp",
            "models/qsqlrelationaltablemodel.cpp", "models/qsqltablemodel.cpp",
        ]
        all_sources = kernel_sources + model_sources

        for src in all_sources:
            obj = os.path.join(build_dir, os.path.basename(src) + ".o")
            self.run(f'clang++ {cflags} {includes} -c {os.path.join(sql_src, src)} -o {obj}')

        moc_files = [f for f in os.listdir(moc_dir) if f.endswith(".h")]
        for mf in moc_files:
            obj = os.path.join(build_dir, mf.replace(".h", ".o"))
            self.run(f'clang++ -x c++ {cflags} {includes} -c {os.path.join(moc_dir, mf)} -o {obj}')

        obj_files = [os.path.join(build_dir, f) for f in os.listdir(build_dir) if f.endswith(".o")]
        obj_args = " ".join(obj_files)
        libQt5Sql = os.path.join(build_dir, "libQt5Sql.so")
        self.run(
            f'clang++ -shared -o {libQt5Sql} {obj_args} '
            f'-L{qt5_pkg}/lib -lQt5Core '
            f'-Wl,-rpath,{qt5_pkg}/lib -Wl,-soname,libQt5Sql.so'
        )

    def _build_mysql_plugin(self):
        qt5_pkg = self._get_qt5_info()
        maria_pkg = self._get_mariadb_info()
        src_dir = self.source_folder
        mysql_src = os.path.join(src_dir, "src", "plugins", "sqldrivers", "mysql")
        build_dir = os.path.join(self.build_folder, "qt5sql_build")
        tmpinc = os.path.join(self.build_folder, "forward_headers")

        maria_inc = os.path.join(maria_pkg, "include", "mariadb")
        maria_lib = os.path.join(maria_pkg, "lib", "mariadb")

        ohos_sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/lib/aarch64-linux-ohos"

        includes = " ".join([
            f"-I{tmpinc}",
            f"-I{qt5_pkg}/include",
            f"-I{qt5_pkg}/include/QtCore",
            f"-I{qt5_pkg}/include/QtCore/5.15.2/QtCore/private",
            f"-I{qt5_pkg}/include/QtCore/5.15.2/QtCore",
            f"-I{qt5_pkg}/include/QtSql",
            f"-I{qt5_pkg}/include/QtSql/5.15.2/QtSql/private",
            f"-I{qt5_pkg}/include/QtSql/5.15.2/QtSql",
            f"-I{tmpinc}/QtSql",
            f"-I{qt5_pkg}/src/sql",
            f"-I{qt5_pkg}/src/corelib",
            f"-I{qt5_pkg}/src/corelib/global",
            f"-I{maria_inc}",
            f"-I{qt5_pkg}/mkspecs/linux-clang",
            f"-I{build_dir}",
        ])

        cflags = (
            "-pipe -O2 -std=c++14 -Wall -Wextra -Wno-deprecated-declarations -fPIC "
            "-D_REENTRANT -DQT_NO_CAST_TO_ASCII -DQT_NO_CAST_FROM_ASCII -DQT_NO_DEBUG "
            "-DQT_PLUGIN -DQT_SQL_LIB -DQT_CORE_LIB"
        )

        moc = os.path.join(qt5_pkg, "bin", "moc")

        self.run(f'{moc} {os.path.join(mysql_src, "main.cpp")} -o {os.path.join(build_dir, "main.moc")}')

        self.run(f'clang++ {cflags} {includes} -c {os.path.join(mysql_src, "qsql_mysql.cpp")} -o {os.path.join(build_dir, "qsql_mysql.o")}')

        self.run(f'clang++ {cflags} {includes} -c {os.path.join(mysql_src, "main.cpp")} -o {os.path.join(build_dir, "main.o")}')

        libqsqlmysql = os.path.join(build_dir, "libqsqlmysql.so")
        self.run(
            f'clang++ -shared -o {libqsqlmysql} '
            f'{os.path.join(build_dir, "qsql_mysql.o")} '
            f'{os.path.join(build_dir, "main.o")} '
            f'-L{build_dir} -lQt5Sql '
            f'-L{qt5_pkg}/lib -lQt5Core '
            f'-L{maria_lib} -lmariadb '
            f'-L{ohos_sdk_lib} -lohenvironment '
            f'-Wl,-rpath,{qt5_pkg}/lib -Wl,-soname,libqsqlmysql.so'
        )

    def package(self):
        build_dir = os.path.join(self.build_folder, "qt5sql_build")
        conan_copy(self, "libQt5Sql.so", src=build_dir, dst=os.path.join(self.package_folder, "lib"))
        conan_copy(self, "libqsqlmysql.so", src=build_dir, dst=os.path.join(self.package_folder, "plugins", "sqldrivers"))

    def package_info(self):
        self.cpp_info.libs = ["qsqlmysql"]
        self.cpp_info.libdirs = ["lib", "plugins/sqldrivers"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["ohenvironment"]
