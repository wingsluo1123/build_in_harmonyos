import os
import shlex
import subprocess
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class QtUnixodbcConan(ConanFile):
    name = "qt-unixodbc"
    version = "5.15.2"
    description = "Qt5 unixODBC SQL driver plugin (QODBCDriver) for OpenHarmony"
    license = "LGPL-2.1"
    homepage = "https://download.qt.io/archive/qt/5.15/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qt-unixodbc only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(
                    self,
                    url=url,
                    sha256=source_data["sha256"],
                    strip_root=True,
                )
                return
            except ConanException as error:
                self.output.warning(f"Failed to download Qt5 source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download Qt5 source from all mirrors")

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or compilers.get("cxx") or "clang++"

        qt5 = self.dependencies["qt5-qtbase"]
        qt5_pkg = qt5.package_folder

        # Locate OHOS SDK sysroot for libohenvironment
        ohos_sysroot_lib = None
        for base in ["/data/service/hnp", "/system"]:
            for root, dirs, files in os.walk(base):
                if "libohenvironment.so" in files:
                    ohos_sysroot_lib = root
                    break
                if len(root) > 80:  # limit depth
                    break
            if ohos_sysroot_lib:
                break
        if not ohos_sysroot_lib:
            ohos_sysroot_lib = ""
            self.output.warning("libohenvironment.so not found in OHOS SDK")

        jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)

        # ── Step 1: Build unixODBC from source ──────────────────────────
        self._build_unixodbc(cxx, cc, jobs)

        unixodbc_prefix = os.path.join(self.build_folder, "unixodbc_install")
        unixodbc_inc = os.path.join(unixodbc_prefix, "include")
        unixodbc_lib = os.path.join(unixodbc_prefix, "lib")

        # ── Step 2: Build Qt5Sql from source ────────────────────────────
        self._build_qt5sql(cxx, cc, src_dir, qt5_pkg, ohos_sysroot_lib)

        # ── Step 3: Build ODBC driver plugin ──────────────────────────
        self._build_odbc_plugin(cxx, cc, src_dir, qt5_pkg, ohos_sysroot_lib,
                                 unixodbc_inc, unixodbc_lib)

    def _build_unixodbc(self, cxx, cc, jobs):
        """Download and build unixODBC from the pre-configured release tarball."""
        uo_url = "https://github.com/lurcher/unixODBC/releases/download/2.3.12/unixODBC-2.3.12.tar.gz"
        uo_sha256 = "f210501445ce21bf607ba51ef8c125e10e22dffdffec377646462df5f01915ec"
        uo_dir = os.path.join(self.build_folder, "unixodbc_src")
        os.makedirs(uo_dir, exist_ok=True)
        # Use Conan's get() for reliable download + SHA256 verification + extraction
        get(self, url=uo_url, sha256=uo_sha256, strip_root=True, destination=uo_dir)

        # Update config.guess/config.sub (2015-era files don't recognize OHOS)
        # Find autoconf build-aux directory dynamically
        autoconf_aux = None
        for candidate in [
            "/data/service/hnp/autoconf.org/autoconf_2.72/share/autoconf/build-aux",
            "/data/service/hnp/autoconf.org/autoconf_2.71/share/autoconf/build-aux",
            "/usr/share/autoconf/build-aux",
            "/system/share/autoconf/build-aux",
        ]:
            if os.path.isfile(os.path.join(candidate, "config.guess")):
                autoconf_aux = candidate
                break
        if not autoconf_aux:
            self.output.warning("autoconf build-aux not found, skipping config.guess update")
        else:
            import shutil
            for subdir in ["", "libltdl"]:
                for cfgfile in ("config.guess", "config.sub"):
                    src = os.path.join(autoconf_aux, cfgfile)
                    dst = os.path.join(uo_dir, subdir, cfgfile) if subdir else os.path.join(uo_dir, cfgfile)
                    if os.path.isfile(src) and os.path.isfile(os.path.join(os.path.dirname(dst), "config.sub")):
                        shutil.copy2(src, dst)
                        self.output.info(f"Updated {cfgfile} in {subdir or 'root'}")
                # Patch config.guess to recognize HarmonyOS as a Linux variant
                cg = os.path.join(uo_dir, subdir, "config.guess") if subdir else os.path.join(uo_dir, "config.guess")
                if os.path.isfile(cg):
                    self._sed_replace(cg, "Linux|GNU|GNU/*)", "HarmonyOS|Linux|GNU|GNU/*)")

        # E011: Fix umask 077 → 022 for HMDFS compatibility
        for cfg in ["configure", "libltdl/configure", "config.guess", "libltdl/config.guess"]:
            cfg_path = os.path.join(uo_dir, cfg)
            if os.path.isfile(cfg_path):
                self._sed_replace(cfg_path, "umask 077", "umask 022")

        uo_prefix = os.path.join(self.build_folder, "unixodbc_install")
        # Set umask 022 to fix E011 (HMDFS temp dir permission issue in config.guess)
        # Use env to set CC/CXX so configure finds the compiler (E001 fix)
        build_triplet = "aarch64-unknown-linux-gnu"
        self.run(
            f'cd "{uo_dir}" && umask 022 && ./configure '
            f'--build={build_triplet} '
            f'--prefix="{uo_prefix}" --enable-shared --disable-static '
            f'--enable-gui=no --enable-drivers=no',
            env=[f'CC={cc}', f'CXX={cxx}'],
        )
        self.run(f'cd "{uo_dir}" && umask 022 && make -j{jobs}',
                 env=[f'CC={cc}', f'CXX={cxx}'])
        self.run(f'cd "{uo_dir}" && umask 022 && make install',
                 env=[f'CC={cc}', f'CXX={cxx}'])

    @staticmethod
    def _sed_replace(filepath, old, new):
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        content = content.replace(old, new)
        with open(filepath, "w", encoding="utf-8", errors="ignore") as f:
            f.write(content)

    @staticmethod
    def _sha256_file(filepath):
        import hashlib
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _build_qt5sql(self, cxx, cc, src_dir, qt5_pkg, ohos_lib):
        """Build Qt5Sql library by manually compiling the SQL module source files."""
        # Copy config headers from qt5-qtbase package to source include tree
        # (qtsql-config.h was generated during qt5-qtbase build but not in include/QtSql/)
        import shutil

        # Public config: <QtSql/qtsql-config.h> → include/QtSql/
        # Private config: <QtSql/private/qtsql-config_p.h> → include/QtSql/5.15.2/QtSql/private/
        sql_config_src = os.path.join(qt5_pkg, "src", "sql")
        sql_public_dst = os.path.join(src_dir, "include", "QtSql")
        sql_private_dst = os.path.join(src_dir, "include", "QtSql", "5.15.2", "QtSql", "private")
        os.makedirs(sql_private_dst, exist_ok=True)
        for cfg_h in ("qtsql-config.h", "qtsql-config_p.h"):
            src_h = os.path.join(sql_config_src, cfg_h)
            # Copy to public include dir
            dst_pub = os.path.join(sql_public_dst, cfg_h)
            if os.path.isfile(src_h) and not os.path.isfile(dst_pub):
                shutil.copy2(src_h, dst_pub)
                self.output.info(f"Copied {cfg_h} to include/QtSql/")
            # Copy to private include dir
            dst_priv = os.path.join(sql_private_dst, cfg_h)
            if os.path.isfile(src_h) and not os.path.isfile(dst_priv):
                shutil.copy2(src_h, dst_priv)
                self.output.info(f"Copied {cfg_h} to include/QtSql/5.15.2/QtSql/private/")

        # Also copy QtCore config headers
        core_config_src = os.path.join(qt5_pkg, "src", "corelib")
        core_public_dst = os.path.join(src_dir, "include", "QtCore")
        core_private_dst = os.path.join(src_dir, "include", "QtCore", "5.15.2", "QtCore", "private")
        os.makedirs(core_private_dst, exist_ok=True)
        for cfg_h in ("qtcore-config.h", "qtcore-config_p.h"):
            src_h = os.path.join(core_config_src, cfg_h)
            dst_pub = os.path.join(core_public_dst, cfg_h)
            if os.path.isfile(src_h) and not os.path.isfile(dst_pub):
                shutil.copy2(src_h, dst_pub)
                self.output.info(f"Copied {cfg_h} to include/QtCore/")
            dst_priv = os.path.join(core_private_dst, cfg_h)
            if os.path.isfile(src_h) and not os.path.isfile(dst_priv):
                shutil.copy2(src_h, dst_priv)
                self.output.info(f"Copied {cfg_h} to include/QtCore/5.15.2/QtCore/private/")

        qt5_inc = os.path.join(qt5_pkg, "include")
        qt5_inc_core = os.path.join(qt5_inc, "QtCore", "5.15.2", "QtCore", "private")
        qt5_inc_core_parent = os.path.join(qt5_inc, "QtCore", "5.15.2", "QtCore")
        qt5_inc_core_vers = os.path.join(qt5_inc, "QtCore", "5.15.2")
        qt5_inc_sql = os.path.join(qt5_inc, "QtSql", "5.15.2", "QtSql", "private")
        qt5_inc_sql_parent = os.path.join(qt5_inc, "QtSql", "5.15.2", "QtSql")
        qt5_inc_sql_vers = os.path.join(qt5_inc, "QtSql", "5.15.2")
        qt5_src = os.path.join(qt5_pkg, "src")

        src_inc = os.path.join(src_dir, "include")
        src_inc_sql_vers = os.path.join(src_inc, "QtSql", "5.15.2")
        src_inc_core_vers = os.path.join(src_inc, "QtCore", "5.15.2")
        src_corelib = os.path.join(src_dir, "src", "corelib")
        src_sql_kernel = os.path.join(src_dir, "src", "sql", "kernel")
        src_sql_models = os.path.join(src_dir, "src", "sql", "models")
        src_mkspecs = os.path.join(src_dir, "mkspecs", "linux-clang")

        include_flags = [
            f"-I{qt5_inc}",
            f"-I{qt5_inc_core}",
            f"-I{qt5_inc_core_parent}",
            f"-I{qt5_inc_core_vers}",
            f"-I{qt5_inc_sql}",
            f"-I{qt5_inc_sql_parent}",
            f"-I{qt5_inc_sql_vers}",
            f"-I{qt5_src}",
            f"-I{src_inc}",
            f"-I{src_inc}/QtCore",
            f"-I{src_inc}/QtSql",
            f"-I{src_inc_core_vers}",
            f"-I{src_inc_sql_vers}",
            f"-I{src_corelib}",
            f"-I{src_corelib}/global",
            f"-I{src_sql_kernel}",
            f"-I{src_sql_models}",
            f"-I{src_mkspecs}",
        ]

        defines = [
            "-DQT_NO_USING_NAMESPACE",
            "-DQT_NO_CAST_FROM_ASCII",
            "-DQT_NO_FOREACH",
            "-DQT_BUILD_SQL_LIB",
            "-DQT_CORE_LIB",
            "-DQT_SQL_LIB",
        ]

        common_flags = [
            "-c", "-pipe", "-O2", "-std=c++14",
            "-Wall", "-Wextra", "-Wno-deprecated-declarations",
            "-D_REENTRANT", "-fPIC",
        ]

        if str(self.settings.os) == "OHOS":
            defines.append("-DQ_OS_OHOS")

        cxx_flags = " ".join(common_flags + defines + include_flags)
        qt5_lib = os.path.join(qt5_pkg, "lib")
        qt5_bin = os.path.join(qt5_pkg, "bin")
        moc = os.path.join(qt5_bin, "moc")

        # Run moc on headers that have Q_OBJECT (generates meta-object code)
        moc_headers = []
        for subdir in ["kernel", "models"]:
            hdr_dir = os.path.join(src_dir, "src", "sql", subdir)
            for fname in sorted(os.listdir(hdr_dir)):
                if fname.endswith(".h"):
                    hdr_path = os.path.join(hdr_dir, fname)
                    with open(hdr_path, "r", errors="ignore") as f:
                        content = f.read()
                    if "Q_OBJECT" in content or "Q_GADGET" in content:
                            moc_headers.append(hdr_path)

        moc_flags = " ".join(defines + include_flags)
        moc_objs = []
        for hdr in moc_headers:
            base = os.path.splitext(os.path.basename(hdr))[0]
            moc_cpp = os.path.join(self.build_folder, f"moc_{base}.cpp")
            moc_obj = os.path.join(self.build_folder, f"moc_{base}.o")
            self.run(f'{shlex.quote(moc)} {moc_flags} "{hdr}" -o "{moc_cpp}"')
            self.run(f'{shlex.quote(cxx)} {cxx_flags} "{moc_cpp}" -o "{moc_obj}"')
            moc_objs.append(moc_obj)

        # Compile all SQL source files
        sql_src_dirs = [src_sql_kernel, src_sql_models]
        obj_files = list(moc_objs)
        for src_dir_local in sql_src_dirs:
            for fname in sorted(os.listdir(src_dir_local)):
                if not fname.endswith(".cpp"):
                    continue
                src_file = os.path.join(src_dir_local, fname)
                obj_file = os.path.join(self.build_folder, fname.replace(".cpp", ".o"))
                self.run(f'{shlex.quote(cxx)} {cxx_flags} "{src_file}" -o "{obj_file}"')
                obj_files.append(obj_file)

        # Link into libQt5Sql.so
        sql_so = os.path.join(self.build_folder, "libQt5Sql.so")
        link_flags = [
            "-shared",
            f"-Wl,-soname,libQt5Sql.so",
            "-Wl,-rpath," + qt5_lib,
        ]
        link_libs = [f"-L{qt5_lib}", "-lQt5Core"]
        if ohos_lib:
            link_libs.append(f"-L{ohos_lib}")
            link_libs.append("-lohenvironment")

        objs = " ".join(f'"{o}"' for o in obj_files)
        libs = " ".join(link_libs)
        lflags = " ".join(link_flags)
        self.run(f'{shlex.quote(cxx)} {lflags} {objs} {libs} -o "{sql_so}"')

    def _build_odbc_plugin(self, cxx, cc, src_dir, qt5_pkg, ohos_lib,
                           unixodbc_inc, unixodbc_lib):
        """Build the ODBC SQL driver plugin (libqsqlodbc.so)."""
        odbc_src = os.path.join(src_dir, "src", "plugins", "sqldrivers", "odbc")
        qt5_inc = os.path.join(qt5_pkg, "include")
        qt5_inc_core = os.path.join(qt5_inc, "QtCore", "5.15.2", "QtCore", "private")
        qt5_inc_core_parent = os.path.join(qt5_inc, "QtCore", "5.15.2", "QtCore")
        qt5_inc_core_vers = os.path.join(qt5_inc, "QtCore", "5.15.2")
        qt5_inc_sql = os.path.join(qt5_inc, "QtSql", "5.15.2", "QtSql", "private")
        qt5_inc_sql_parent = os.path.join(qt5_inc, "QtSql", "5.15.2", "QtSql")
        qt5_inc_sql_vers = os.path.join(qt5_inc, "QtSql", "5.15.2")
        qt5_src = os.path.join(qt5_pkg, "src")
        qt5_bin = os.path.join(qt5_pkg, "bin")
        qt5_lib = os.path.join(qt5_pkg, "lib")

        src_inc = os.path.join(src_dir, "include")
        src_inc_sql_vers = os.path.join(src_inc, "QtSql", "5.15.2")
        src_inc_core_vers = os.path.join(src_inc, "QtCore", "5.15.2")
        src_corelib = os.path.join(src_dir, "src", "corelib")
        src_mkspecs = os.path.join(src_dir, "mkspecs", "linux-clang")

        include_flags = [
            f"-I{odbc_src}",
            f"-I{qt5_inc}",
            f"-I{qt5_inc_core}",
            f"-I{qt5_inc_core_parent}",
            f"-I{qt5_inc_core_vers}",
            f"-I{qt5_inc_sql}",
            f"-I{qt5_inc_sql_parent}",
            f"-I{qt5_inc_sql_vers}",
            f"-I{qt5_src}",
            f"-I{src_inc}",
            f"-I{src_inc}/QtCore",
            f"-I{src_inc}/QtSql",
            f"-I{src_inc_core_vers}",
            f"-I{src_inc_sql_vers}",
            f"-I{src_corelib}",
            f"-I{src_corelib}/global",
            f"-I{src_mkspecs}",
            f"-I{unixodbc_inc}",
        ]

        defines = [
            "-DQT_NO_CAST_TO_ASCII",
            "-DQT_NO_CAST_FROM_ASCII",
            "-DQT_PLUGIN",
            "-DQT_SQL_LIB",
            "-DQT_CORE_LIB",
            "-DUNICODE",
        ]

        if str(self.settings.os) == "OHOS":
            defines.append("-DQ_OS_OHOS")

        common_flags = [
            "-c", "-pipe", "-O2", "-std=c++14",
            "-Wall", "-Wextra", "-Wno-deprecated-declarations",
            "-D_REENTRANT", "-fPIC",
        ]

        cxx_flags = " ".join(common_flags + defines + include_flags)

        # Run moc on main.cpp to generate main.moc
        moc = os.path.join(qt5_bin, "moc")
        moc_flags = " ".join(defines + include_flags)
        main_moc = os.path.join(odbc_src, "main.moc")
        self.run(
            f'{shlex.quote(moc)} {moc_flags} '
            f'"{os.path.join(odbc_src, "main.cpp")}" -o "{main_moc}"'
        )

        # Run moc on qsql_odbc_p.h
        moc_odbc = os.path.join(self.build_folder, "moc_qsql_odbc_p.cpp")
        self.run(
            f'{shlex.quote(moc)} {moc_flags} '
            f'"{os.path.join(odbc_src, "qsql_odbc_p.h")}" -o "{moc_odbc}"'
        )

        # Compile qsql_odbc.cpp
        odbc_obj = os.path.join(self.build_folder, "qsql_odbc.o")
        self.run(
            f'{shlex.quote(cxx)} {cxx_flags} '
            f'"{os.path.join(odbc_src, "qsql_odbc.cpp")}" -o "{odbc_obj}"'
        )

        # Compile main.cpp
        main_obj = os.path.join(self.build_folder, "main.o")
        self.run(
            f'{shlex.quote(cxx)} {cxx_flags} '
            f'"{os.path.join(odbc_src, "main.cpp")}" -o "{main_obj}"'
        )

        # Compile moc output for qsql_odbc_p.h
        moc_obj = os.path.join(self.build_folder, "moc_qsql_odbc_p.o")
        self.run(
            f'{shlex.quote(cxx)} {cxx_flags} '
            f'"{moc_odbc}" -o "{moc_obj}"'
        )

        # Link into libqsqlodbc.so
        plugin_so = os.path.join(self.build_folder, "libqsqlodbc.so")
        build_lib = self.build_folder
        link_flags = [
            "-shared",
            "-Wl,-soname,libqsqlodbc.so",
            f"-Wl,-rpath,{qt5_lib}",
        ]
        link_libs = [
            f"-L{build_lib}",
            "-lQt5Sql",
            f"-L{qt5_lib}",
            "-lQt5Core",
            f"-L{unixodbc_lib}",
            "-lodbc",
        ]
        if ohos_lib:
            link_libs.append(f"-L{ohos_lib}")
            link_libs.append("-lohenvironment")

        objs = f'"{odbc_obj}" "{main_obj}" "{moc_obj}"'
        libs = " ".join(link_libs)
        lflags = " ".join(link_flags)
        self.run(f'{shlex.quote(cxx)} {lflags} {objs} {libs} -o "{plugin_so}"')

    def package(self):
        import shutil

        # Copy libqsqlodbc.so to plugins/sqldrivers/
        copy(self, "libqsqlodbc.so",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "plugins", "sqldrivers"),
             keep_path=False)

        # Copy libQt5Sql.so to lib/
        copy(self, "libQt5Sql.so",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)

        # Copy Qt5Sql public headers from qt5-qtbase package
        qt5 = self.dependencies["qt5-qtbase"]
        qt5_pkg = qt5.package_folder
        copy(self, "*",
             src=os.path.join(qt5_pkg, "include", "QtSql"),
             dst=os.path.join(self.package_folder, "include", "QtSql"),
             keep_path=True)

        # Copy config headers that are missing from include/QtSql/
        # (generated during qt5-qtbase build but only in src/sql/)
        sql_config_src = os.path.join(qt5_pkg, "src", "sql")
        sql_public_dst = os.path.join(self.package_folder, "include", "QtSql")
        sql_private_dst = os.path.join(self.package_folder, "include", "QtSql",
                                       "5.15.2", "QtSql", "private")
        os.makedirs(sql_private_dst, exist_ok=True)
        for cfg_h in ("qtsql-config.h", "qtsql-config_p.h"):
            src_h = os.path.join(sql_config_src, cfg_h)
            if os.path.isfile(src_h):
                shutil.copy2(src_h, os.path.join(sql_public_dst, cfg_h))
                shutil.copy2(src_h, os.path.join(sql_private_dst, cfg_h))

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["plugins/sqldrivers"]

        qt5sql = self.cpp_info.components["Qt5Sql"]
        qt5sql.libs = ["Qt5Sql"]
        qt5sql.includedirs = ["include", "include/QtSql"]
        qt5sql.requires = ["qt5-qtbase::Qt5Core"]
        qt5sql.set_property("cmake_file_name", "Qt5Sql")
        qt5sql.set_property("cmake_target_name", "Qt5::Sql")

        qsqlodbc = self.cpp_info.components["qsqlodbc"]
        qsqlodbc.libs = ["qsqlodbc"]
        qsqlodbc.libdirs = ["plugins/sqldrivers"]
        qsqlodbc.requires = ["Qt5Sql", "qt5-qtbase::Qt5Core"]
