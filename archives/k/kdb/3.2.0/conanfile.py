#!/usr/bin/env python3
"""Conan recipe for kdb 3.2.0 (KDE KDb) on HarmonyOS PC.

KDb is KDE's database connectivity library: driver plugin management
(KDbDriverManager/KDbDriverMetaData), connection and transaction handling
(KDbConnection), table/field schema (KDbTableSchema/KDbField), queries and
expressions.  This 3.2.0 tarball is the standalone KDb project (Qt5/KF5 era,
shared with Kexi): libKDb3.so.4.2.0 (upstream set_coinstallable_lib_version
special-cases a 3.x stable major to SOVERSION 4), headers under
include/KDb3/, KDbConfig.cmake under lib/cmake/KDb3, the export name is the
plain `KDb` (KDbTargets.cmake has no namespace).  The library links Qt5
Core/Gui/Widgets + KF5::CoreAddons PUBLIC and Qt5::Xml + ICU::i18n PRIVATE;
the sqlite3 driver (MODULE) and its ICU extension are built and installed to
<prefix>/lib/plugins/kdb3{,/sqlite3}; upstream also installs the
kdb3_sqlite3_dump CLI to bin/ (upstream default; not part of the declared
export).  MySQL/PostgreSQL drivers are optional upstream (find_package
without REQUIRED) and are not built on this image.  Upstream registers 14
ctest entries when BUILD_TESTING=ON (9 KDb API suites + 3 tool tests +
SqlParserTest + the headers_test.sh compile check).

OHOS-specific adaptations (reusing the validated Qt5/KF5 skeleton of the
krunner5 / kcoreaddons5 / qtpositioning5 chain):
  - QT_MAJOR_VERSION=5 selects Qt5 (qt5-qtbase/5.15.2.2, the widgets-capable
    build; 5.15.2 is the -no-widgets stub and is refused).
  - CMAKE_SYSTEM_NAME=Linux: the OHOS Conan toolchain maps os=OHOS to
    CMAKE_SYSTEM_NAME=HarmonyOS, for which CMake defines neither UNIX nor a
    platform module, and the build is flagged as cross-compiling.  KDECMakeSettings
    only applies its POSIX RPATH settings under if(UNIX) and ECM only
    registers the upstream ctest cases when the build is not cross-compiling;
    forcing the Linux platform (same libc / clang driver on OHOS PC) restores
    UNIX=1 and a native build.
  - KF_IGNORE_PLATFORM_CHECK=TRUE is REQUIRED by this source: the root
    CMakeLists.txt includes KDEFrameworkCompilerSettings, which includes
    ECM's KDEMetaInfoPlatformCheck; that module does
    ``file(STRINGS metainfo.yaml ...)`` at include time, and the kdb-3.2.0
    release tarball ships no metainfo.yaml, so with the check enabled
    configure fails reading the file (ECM 6.26 source verified).  With the
    flag set, both the file read and the platform comparison are skipped.
  - KF_SKIP_PO_PROCESSING=ON: ECM 6.26's ecm_install_po_files_as_qm()
    early-returns (KDb calls it for po/), so no Qt5LinguistTools/lrelease is
    needed.
  - KDE_INSTALL_USE_QT_SYS_PATHS=OFF: plugins go to <prefix>/lib/plugins/kdb3
    (KDEInstallDirs5: QTPLUGINDIR = LIBDIR/plugins when not using Qt install
    paths, PLUGINDIR = QTPLUGINDIR).  KDb::libraryPaths() is
    QCoreApplication::libraryPaths() filtered to the entries that contain a
    kdb3 subdirectory, so consumers (autotests via the compile-time
    KDB_LOCAL_PLUGINS_DIR, the test_package via
    QT_PLUGIN_PATH=<prefix>/lib/plugins) bring the driver in through the Qt
    library-path mechanism without touching the install prefix.
  - BUILD_QCH=OFF skips kdb_add_qch(); kdb_install_qch_export() still runs
    unconditionally (upstream) and installs a stub KDbQCHTargets.cmake, so
    consumer KDbConfig.cmake stays complete.
  - PYTHON_EXECUTABLE is pinned to the interpreter running Conan:
    KDbCreateSharedDataClasses runs tools/sdc.py at configure time through
    find_package(PythonInterp 2.6) + execute_process; pre-setting the cache
    variable skips the host search (and survives find_package(PythonInterp)
    removal in CMake 4).
  - SQLITE_INCLUDE_PATH / SQLITE_EXT_INCLUDE_PATH / SQLITE_LIBRARIES are
    pinned to the conan sqlite3 package so FindSqlite's host-side search
    cannot pick up anything else, and its shell probe (find_program sqlite3 +
    ``pragma compile_options``) has nothing to run against; the only option
    the probe actually checks is OMIT_LOAD_EXTENSION (drivers/CMakeLists sets
    SQLITE_LOAD_EXTENSION_REQUIRED ON) and the conan sqlite3 build has
    load-extension support, so the probe outcome is benign either way.
  - ICU_ROOT points at the conan icu package: find_package(ICU REQUIRED i18n
    uc) resolves through the FindICU module bundled in this tree
    (cmake/modules/FindICU.cmake, first entry of CMAKE_MODULE_PATH at root
    CMakeLists line 3; there is no CMakeDeps config for icu in this
    recipe: cmake_find_mode=none).  ICU backs KDb's unicode-aware
    comparisons and links PRIVATE into libKDb3.
    The conan icu package ships static archives only, and FindICU creates
    bare imported libraries with no inter-component dependency edges (the
    shared-library chain would resolve via DT_NEEDED), so
    patches/0002-CMakeLists-static-icu-link-order.patch requests the data
    component and appends i18n -> uc -> data onto the imported targets;
    without it the module link fails on icudt76_dat / _u_* under
    -Wl,--no-undefined.
  - The KF5 aggregate lookup ``find_package(KF5 5.16.0 REQUIRED CoreAddons)``
    resolves through ECM 6.26's find-modules/FindKF5.cmake (the ECM module
    dirs are wired onto CMAKE_MODULE_PATH), which forwards each component to
    find_package(KF5CoreAddons) CONFIG from the kcoreaddons5 prefix.  No
    KF5Config.cmake umbrella package is involved (none exists in this
    archive; ECM's find module is the canonical mechanism).
  - Build/test topology: BUILD_TESTING=ON registers the 13 ecm tests plus
    HeadersTest.  HeadersTest (autotests/headers/headers_test.sh) compiles
    one TU per installed public header against $builddir/install_manifest.txt
    in a generated consumer project, so build() performs an upstream install
    into <build>/stage between cmake.build() and ctest (the manifest is
    written into the build directory).  The generated project's
    find_package(ECM/Qt5/KF5/KDb) calls resolve through a CMAKE_PREFIX_PATH
    environment composed in _run_upstream_tests() (stage + ecm + qtbase +
    kcoreaddons5 + icu + sqlite3); the entries are joined with os.pathsep,
    not ';': CMake treats this environment variable as path-separated and
    takes a semicolon-joined multi-entry value as a single invalid prefix.
    The nested project's
    cmake_minimum_required(2.8.12) needs CMAKE_POLICY_VERSION_MINIMUM=3.5 in
    the environment (CMake initialises the variable from it), because the
    OHOS image ships CMake 4.1.2, which hard-errors on pre-3.5 minimums.
  - CMAKE_POLICY_VERSION_MINIMUM=3.5 is set as a toolchain cache variable as
    well (the minimum-version check reads the cache entry, not a plain
    variable): KDb's own root declares cmake_minimum_required(3.0).
  - patches/0001-SetKDbCMakePolicies-cmake4-cmp0059.patch: CMake 4.x removed
    the OLD behavior of CMP0059, so SetKDbCMakePolicies.cmake's unconditional
    cmake_policy(SET CMP0059 OLD) is a hard error there (hit on the 4.1.2
    image).  The patch guards the OLD set behind CMAKE_VERSION VERSION_LESS
    "4.0"; on CMake >= 4.0 NEW is the only behavior, and every
    add_definitions() call site in this tree runs in the directory that also
    creates its targets, so the switch is equivalent.  Version guard only, no
    platform macros.
  - patches/0003-CMakeLists-scanner-wno-register.patch: the pre-generated
    flex scanner (src/parser/generated/sqlscanner.cpp) still uses the
    'register' storage class; C++17 language modes diagnose it as the
    -Wregister error, so the scanner's compile flags gain -Wno-register next
    to the tree's existing -Wno-deprecated-register (which covers only the
    pre-C++17 wording).
  - patches/0004-autotests-headers-shell-wrapper.patch: the HeadersTest ctest
    entry execve()s autotests/headers/headers_test.sh directly; the target
    image refuses that exec ("Permission denied" although the file carries
    executable bits, while ELF executables from the same tree run).  The
    add_test command wraps the script in `sh`, which is equivalent and
    portable.
  - CMAKE_BUILD_WITH_INSTALL_RPATH=ON (E537): OHOS refuses to mmap PROT_EXEC
    a library whose ELF was rewritten after linking; linking with the final
    install RPATH leaves the install step nothing to rewrite.  Every
    packaged ELF is then re-signed with llvm-objcopy --remove-section
    .codesign + binary-sign-tool -selfSign 1 (krunner5/kcoreaddons5
    precedent).
  - CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE + SONAME flags: relocatable,
    unversioned DT_SONAME (W3 CI L5 soname gate).
  - CMAKE_BUILD_PARALLEL_LEVEL=1: the HMDFS cache refuses the make jobserver
    fifo (EPERM).
  - /system/lib64 is prepended to LD_LIBRARY_PATH while the host tools and
    the tests run so the compatible libc++ wins over the sandbox one.
  - CMAKE_{AUTOMOC,AUTORCC,AUTOUIC}_EXECUTABLE point at the qt5-qtbase bin
    tools, and _prepare_qt_mkspec_compat recreates the build-tree mkspecs
    path that the packaged Qt5CoreConfigExtrasMkspecDir.cmake hard-codes
    (krunner5 / kcoreaddons5 precedent).
  - ECM_MODULE_PATH / ECM_DIR are set explicitly: ecm is a tool_requires
    (build context), so CMakeDeps does not wire its share/ECM tree into the
    host prefix paths.  They are set as toolchain *cache* variables (Conan
    puts those on the cmake command line as -D): KDb's root CMakeLists.txt
    calls find_package(ECM) on line 2, before project(), and CMake reads the
    toolchain file only at the first project()/enable_language().
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KDbConan(ConanFile):
    name = "kdb"
    version = "3.2.0"
    description = "KDE KDb - database connectivity library (driver plugins, connections, schema, queries)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/office/kdb"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # .2 is the widgets/DBus-capable Qt5 build; force=True normalises the
        # graph because kcoreaddons5/5.116.0.1 still pins qt5-qtbase/5.15.2.
        self.requires("qt5-qtbase/5.15.2.2", force=True)
        self.requires("kcoreaddons5/5.116.0.1")
        # ICU is a hard configure-time requirement of KDb (unicode-aware
        # string comparisons; links PRIVATE into libKDb3 and the sqlite ICU
        # extension).
        self.requires("icu/76.1")
        # The SQLite driver is the only database backend built (the MySQL/
        # PostgreSQL drivers are optional upstream and absent here).
        self.requires("sqlite3/3.49.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # qt5-qtbase is consumed through its native Qt5 configs; the
        # CMakeDeps-generated ones would shadow them and do not carry the
        # mkspec include path.
        deps.set_property("qt5-qtbase", "cmake_find_mode", "none")
        # icu is consumed through the tree's bundled FindICU module
        # (ICU_ROOT is pinned below); a generated icu config would shadow
        # that module and would not provide the ICU::i18n/ICU::uc component
        # targets KDb links.
        deps.set_property("icu", "cmake_find_mode", "none")
        # sqlite3 is consumed through KDb's own cmake/modules/FindSqlite.cmake
        # (drivers/CMakeLists); the cache pins below feed it directly.
        deps.set_property("sqlite3", "cmake_find_mode", "none")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        # See module docstring: the release tarball has no metainfo.yaml and
        # KDEFrameworkCompilerSettings' KDEMetaInfoPlatformCheck would fail
        # reading it at include time.
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # Treat OHOS as a Linux-like target so CMake defines UNIX and does
        # not report a cross build: KDECMakeSettings applies its POSIX RPATH
        # settings and ECM registers the upstream ctest cases.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # CMake 4.1.2 on the OHOS image: KDb's root cmake_minimum_required is
        # 3.0, below the removed < 3.5 compatibility tier.  The minimum
        # check reads the cache entry (a plain toolchain variable is ignored),
        # matching the repository precedent (julius / milkytracker /
        # sdl2_mixer recipes).
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # HMDFS cannot create the make jobserver fifo (EPERM).
        tc.variables["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        # E537: link with the final install RPATH so the install step does
        # not rewrite the ELF in place.
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "ON"
        # Relocatable, unversioned DT_SONAME (W3 CI L5 soname gate).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        # tools/sdc.py (KDbCreateSharedDataClasses) runs at configure time
        # through find_package(PythonInterp 2.6) + execute_process.
        tc.variables["PYTHON_EXECUTABLE"] = sys.executable

        qtbase = self.dependencies["qt5-qtbase"]
        icu = self.dependencies["icu"]
        sqlite3 = self.dependencies["sqlite3"]

        # ICU: FindICU's root hint.
        tc.variables["ICU_ROOT"] = icu.package_folder
        # FindSqlite: pre-seeded cache entries win over its find_path/
        # find_library search (and over any host sqlite3.h), see module
        # docstring.
        sqlite_include = os.path.join(sqlite3.package_folder, "include")
        tc.variables["SQLITE_INCLUDE_PATH"] = sqlite_include
        tc.variables["SQLITE_EXT_INCLUDE_PATH"] = sqlite_include
        tc.variables["SQLITE_LIBRARIES"] = os.path.join(
            sqlite3.package_folder, "lib", "libsqlite3.a"
        )

        # Qt5CoreConfigExtrasMkspecDir.cmake hard-codes a build-tree path
        # (<prefix>/../b/mkspecs/linux-clang) the packaged cache entry never
        # has; recreate it from the package's own mkspecs/
        # (krunner5 / kcoreaddons5 precedent).
        self._prepare_qt_mkspec_compat(qtbase.package_folder)

        qbin = os.path.join(qtbase.package_folder, "bin")
        for tool, cmake_var in (
            ("moc", "CMAKE_AUTOMOC_EXECUTABLE"),
            ("rcc", "CMAKE_AUTORCC_EXECUTABLE"),
            ("uic", "CMAKE_AUTOUIC_EXECUTABLE"),
        ):
            tool_path = os.path.join(qbin, tool)
            if not os.path.isfile(tool_path):
                raise ConanInvalidConfiguration(
                    "qt5-qtbase/5.15.2.2 does not provide the required "
                    "bin/{} tool".format(tool)
                )
            tc.variables[cmake_var] = tool_path

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            # KDb's root CMakeLists.txt calls find_package(ECM) *before*
            # project() (line 2), and CMake only processes the toolchain file
            # at the first project()/enable_language() -- recipes whose root
            # uses the newer project()-first order (krunner5 etc.) could use
            # plain toolchain variables here, but for KDb these two must
            # arrive as command-line -D cache entries (Conan passes
            # cache_variables that way) to be visible at line 2.
            tc.cache_variables["ECM_DIR"] = os.path.join(ecm_share, "cmake")
            # The find-modules dir carries FindKF5.cmake (the module the
            # project's aggregate find_package(KF5 ... CoreAddons) resolves
            # through).
            tc.cache_variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        tc.generate()

        # Wire the search paths CMakeDeps cannot provide.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for pkg in (qtbase, icu, sqlite3):
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % pkg.package_folder)
            lines.append('list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % pkg.package_folder)
            lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % pkg.package_folder)
        # The KF5 dependency packages are consumed through their native
        # KF5*Config.cmake files (their recipes publish
        # cmake_find_mode=none), so their prefixes must be wired here.
        dep = self.dependencies.get("kcoreaddons5")
        if dep and dep.package_folder:
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % dep.package_folder)
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")'
                % dep.package_folder
            )
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append('list(PREPEND CMAKE_MODULE_PATH "%s")' % ecm_cmake)
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % ecm_cmake)
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # The whole mkspecs tree is needed: <qplatformdefs.h> is included
        # from the mkspec include dir, and Qt5CoreConfigExtras.cmake resolves
        # it as <package_folder>/../b/mkspecs (the build tree of the
        # original build), which the packaged cache entry never has.
        source = os.path.join(qt_package_folder, "mkspecs")
        expected = os.path.join(os.path.dirname(qt_package_folder), "b", "mkspecs")
        if not os.path.isdir(source):
            return
        os.makedirs(expected, exist_ok=True)
        for name in os.listdir(source):
            src_entry = os.path.join(source, name)
            dst_entry = os.path.join(expected, name)
            if os.path.exists(dst_entry):
                continue
            if os.path.isdir(src_entry):
                shutil.copytree(src_entry, dst_entry)
            else:
                shutil.copy2(src_entry, dst_entry)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        # HeadersTest (autotests/headers/headers_test.sh) compiles one TU per
        # installed public header; it reads <build>/install_manifest.txt and
        # a generated consumer project resolves KDb through a stage prefix,
        # so the upstream install must run before ctest.
        self._stage_install()
        self._run_upstream_tests()

    def _stage_install(self):
        stage = os.path.join(self.build_folder, "stage")
        with self._runtime_env().vars(self).apply():
            self.run(
                'cmake --install "{}" --prefix "{}"'.format(self.build_folder, stage)
            )

    def _runtime_env(self):
        runtime_env = Environment()
        qt5 = self.dependencies.get("qt5-qtbase")
        if qt5 and qt5.package_folder:
            runtime_env.prepend_path(
                "PATH", os.path.join(qt5.package_folder, "bin")
            )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        # Build-tree locations: libKDb3.so (src/), the sqlite driver and its
        # ICU extension (plugins/kdb3, loaded through
        # KDB_LOCAL_PLUGINS_DIR by the autotests).
        for rel in ("src", "lib", "bin"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        if str(self.settings.os) == "OHOS":
            # The sandbox LD_LIBRARY_PATH carries an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64;
            # prepend /system/lib64 so the Qt host tools and the test
            # executables resolve the compatible libc++ first.
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return runtime_env

    def _run_upstream_tests(self):
        # 14 upstream ctest entries: 9 KDb API suites + 3 tool tests +
        # SqlParserTest + HeadersTest (the last one is a nested configure/
        # build against the stage install, see build()).
        if not can_run(self):
            return
        test_env = self._runtime_env()
        # The nine DB suites and SqlParserTest link the in-tree helper
        # library libkdbtestutils.so (linked into <build>/autotests) and the
        # in-tree libKDb3.so; with CMAKE_BUILD_WITH_INSTALL_RPATH=ON the
        # binaries carry no build-tree RPATH (their recorded RPATH is the
        # not-yet-existing package prefix), so the build directories are
        # provided through the environment.
        for build_subdir in ("autotests", "src", "lib"):
            test_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, build_subdir))
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        # CMake >= 4 hard-errors on the generated HeadersTest project's
        # cmake_minimum_required(2.8.12); the variable is initialised from
        # the environment (verified CMake behaviour) and reaches the nested
        # cmake through the ctest environment.
        test_env.define("CMAKE_POLICY_VERSION_MINIMUM", "3.5")
        # The nested HeadersTest project resolves its dependencies through
        # the environment: stage install first, then the packages the stage's
        # KDbConfig.cmake and the generated project find via
        # find_package(ECM/Qt5/KF5/KDb).
        search_paths = [os.path.join(self.build_folder, "stage")]
        for name in ("qt5-qtbase", "kcoreaddons5", "icu", "sqlite3"):
            dep = self.dependencies.get(name)
            if dep and dep.package_folder:
                search_paths.append(dep.package_folder)
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            search_paths.append(os.path.join(ecm.package_folder, "share", "ECM", "cmake"))
        # The CMAKE_PREFIX_PATH environment variable is path-separated
        # (os.pathsep), not a CMake ';' list: CMake joins the entries only
        # on the platform path separator, while a semicolon-joined
        # multi-entry value is taken as one invalid prefix (device-verified:
        # a semicolon-joined value fails find_package(ECM), the
        # colon-joined value resolves all six prefixes).
        test_env.define("CMAKE_PREFIX_PATH", os.pathsep.join(search_paths))
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        try:
            os.chmod(xdg_runtime, 0o700)
        except OSError:
            pass
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        # HeadersTest spawns autotests/headers/headers_test.sh: the source
        # patch registers it through `sh` (the target image refuses to
        # execve() the script directly, "Permission denied").
        ctest_cmd = 'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
            self.build_folder
        )
        with test_env.vars(self).apply():
            self.run(ctest_cmd)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder):
        """CMake rewrites the RUNPATH of installed shared libraries, which
        invalidates the OHOS build-time .codesign section. The OHOS loader
        then refuses to load the library ("Permission denied"). Re-sign every
        packaged ELF (kitemmodels 6.18.0.1 / kirigami 6.26.0 / ki18n 6.26.0.1
        precedent)."""
        if str(self.settings.os) not in ("OHOS", "HarmonyOS") or not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException("Cannot locate OHOS ELF signing tools")
        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(
                    f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}",
                    ignore_errors=True,
                )
                self.run(
                    f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                    f"-outFile {self._quote(path)} -selfSign 1"
                )
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package(self):
        cmake = CMake(self)
        # install() runs cmake again (env-clean CI shell: no /system/lib64 on
        # LD_LIBRARY_PATH -> the cmake binary itself fails to relocate,
        # exit 127); wrap it with the runtime env like build().
        with self._runtime_env().vars(self).apply():
            cmake.install()
        self._sign_ohos_elf_tree(self.package_folder)

    def package_info(self):
        # The project installs its own KDbConfig.cmake (target export name
        # `KDb`, lib/cmake/KDb3) with proper dependency tracking; use
        # cmake_find_mode=none so CMakeDeps does not shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KDb3"]
