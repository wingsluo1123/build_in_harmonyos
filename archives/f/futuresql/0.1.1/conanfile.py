#!/usr/bin/env python3
"""Conan recipe for futuresql 0.1.1 on HarmonyOS PC.

futuresql runs SQL queries on a dedicated database thread and exposes the
results through QFuture (libfuturesql6.so, CMake package FutureSQL6, target
FutureSQL6::FutureSQL).

OHOS-specific adaptations:
  - qtbase-sql-dbus/6.11.1 is the Qt6 build that ships Qt6Sql and the QSQLITE
    driver plugin; the baseline qtbase package is built with FEATURE_sql=OFF.
    futuresql is a SQL-only library, so it links the sql-dbus Qt.
  - Both Qt packages set cmake_find_mode=none and ship Qt's own Qt6Config.cmake,
    so CMakeDeps emits no Qt config file: the recipe points Qt6_DIR and
    CMAKE_PREFIX_PATH at the qtbase-sql-dbus package and writes
    conan_cmakedeps_paths.cmake itself (kcodecs/6.26.0 precedent).
  - ECM_MODULE_PATH is set manually: ecm is a build-context tool_requires and
    CMakeDeps generates no config for it; the real ECMConfig.cmake from the
    package is located through CMAKE_PREFIX_PATH.
  - BUILD_TESTING=ON: the upstream sqlitetest is built and run through ctest.
    Its coroutine code needs QCoro6::Core, declared with test_requires so that
    qcoro (and its baseline qtbase) does not propagate to consumers.
  - CMake has no Platform/HarmonyOS module, so CMAKE_SHARED_LIBRARY_SONAME_*
    stays empty and lld emits no DT_SONAME. Inject the Linux-style flag so the
    SONAME is recorded (L5a/L5c). The build filesystem (HMDFS) refuses
    symlink(2), so CMake's VERSION/SOVERSION symlink chain cannot be created;
    a runtime capability probe switches CMAKE_PLATFORM_NO_VERSIONED_SONAME on
    (DRAFT-7341 libtiff precedent) and the library is installed as a single
    unversioned libfuturesql6.so that still carries DT_SONAME.
"""
import errno
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class FuturesqlConan(ConanFile):
    name = "futuresql"
    version = "0.1.1"
    description = "FutureSQL — non-blocking SQL database framework for Qt (Qt6)"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/libraries/futuresql"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Only qtbase-sql-dbus ships Qt6Sql (FEATURE_sql=ON) plus the QSQLITE
        # driver plugin that FutureSQL's SQLite backend requires.
        self.requires("qtbase-sql-dbus/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")
        # Upstream autotests are QCoro coroutines (QCoro::Task / QCoro::Future).
        # test_requires keeps qcoro and its baseline qtbase out of the
        # consumers' dependency graph.
        self.test_requires("qcoro/0.13.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _symlinks_supported(self):
        """Probe symlink(2) support in the generators folder.

        CMake creates the VERSION/SOVERSION symlink chain at link time; on
        HMDFS that call fails with EACCES/EPERM (Permission denied) and
        aborts the build. Detect the capability at generate() time instead
        of branching on a platform macro (DRAFT-7341 libtiff precedent).
        Only file-system refusals are treated as "no symlinks"; unrelated
        I/O errors propagate so they are not silently turned into an
        unversioned package layout.
        """
        probe_dir = self.generators_folder
        target = os.path.join(probe_dir, ".symlink-probe-target")
        link = os.path.join(probe_dir, ".symlink-probe-link")
        os.makedirs(probe_dir, exist_ok=True)
        with open(target, "w") as handle:
            handle.write("probe")
        try:
            if os.path.lexists(link):
                os.remove(link)
            os.symlink(target, link)
            supported = True
        except NotImplementedError:
            supported = False
        except OSError as exc:
            # HMDFS answers symlink(2) with EACCES (Permission denied);
            # EPERM/ENOSYS/EOPNOTSUPP cover the other documented refusals.
            if exc.errno not in (
                errno.EACCES,
                errno.EPERM,
                errno.ENOSYS,
                errno.EOPNOTSUPP,
            ):
                raise
            supported = False
        finally:
            for path in (link, target):
                try:
                    os.remove(path)
                except OSError:
                    pass
        self.output.info(
            "symlink probe: %s" % ("supported" if supported else "unsupported")
        )
        return supported

    def generate(self):
        # CMakeDeps is still needed for the non-Qt transitive packages of
        # qtbase-sql-dbus (dbus, expat). qcoro's real upstream config is
        # preferred at configure time -- see _write_cmake_paths.
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # ECM defaults QT_MAJOR_VERSION to 6 (ECM >= 5.240), pin it so the Qt6
        # code paths (KDEInstallDirs6, ECMQueryQt -> Qt6::qtpaths) are always
        # selected.
        tc.variables["QT_MAJOR_VERSION"] = 6
        if self.settings.os == "OHOS":
            # Native builds stay in CMake's Generic platform module (there is
            # no Platform/HarmonyOS), which has no shared-library soname rule.
            # Without this flag the installed library has no DT_SONAME, which
            # breaks the exported target for consumers (L5a/L5c).
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            if not self._symlinks_supported():
                # CMake's cmake_symlink_library step needs real symlinks for
                # the upstream SOVERSION 0 chain (libfuturesql6.so -> .so.0).
                # HMDFS on the device returns EACCES for symlink(2), aborting
                # the link step. Keep SONAME emission (injected above) but let
                # CMake skip the versioned names (DRAFT-7341 libtiff
                # precedent). Other platforms keep the upstream layout.
                tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        qt = self.dependencies.get("qtbase-sql-dbus")
        if qt:
            tc.variables["Qt6_DIR"] = os.path.join(
                qt.package_folder, "lib", "cmake", "Qt6"
            )

        self._write_cmake_paths(qt, ecm)
        tc.generate()

    def _write_cmake_paths(self, qt, ecm):
        """Write conan_cmakedeps_paths.cmake (auto-included by the toolchain).

        CMakeDeps generates no config for packages with cmake_find_mode=none,
        so their builddirs are missing from CMAKE_PREFIX_PATH. Add them here,
        keeping qtbase-sql-dbus ahead of everything else.
        """
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized and normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if not dep or not dep.package_folder:
                continue
            # The baseline qtbase (pulled in by qcoro) is built with
            # FEATURE_sql=OFF; never let it shadow qtbase-sql-dbus.
            if dep.ref.name == "qtbase":
                continue
            add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
            add_unique(prefixes, dep.package_folder)
            add_unique(libraries, os.path.join(dep.package_folder, "lib"))
            add_unique(includes, os.path.join(dep.package_folder, "include"))
            add_unique(modules, os.path.join(dep.package_folder, "lib", "cmake"))

        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            add_unique(prefixes, os.path.join(ecm_share, "cmake"))
            for rel in ("modules", "find-modules", "kde-modules"):
                add_unique(modules, os.path.join(ecm_share, rel))

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{";".join(modules)};${{CMAKE_MODULE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        # The CMakeDeps-generated QCoro6Config.cmake only declares the Conan
        # component targets; the upstream project also calls
        # qcoro_enable_coroutines(), which is installed by QCoro itself in
        # <qcoro>/lib/cmake/QCoro6Coro/QCoroMacros.cmake and reached through
        # QCoro6Config -> QCoro6CoreConfig -> find_dependency(QCoro6Coro).
        # Prepend the real package cmake dir in front of the generators folder
        # so find_package(QCoro6) loads that config chain instead.
        qcoro = self.dependencies.get("qcoro")
        if qcoro and qcoro.package_folder:
            qcoro_cmake = os.path.join(qcoro.package_folder, "lib", "cmake")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qcoro_cmake}")')
        if qt and qt.package_folder:
            qt_pkg = qt.package_folder.replace("\\", "/")
            # Prepended last: highest search priority for Qt's own Qt6Config.
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')

        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as handle:
            handle.write("\n".join(lines) + "\n")

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _sdk_llvm_lib_dirs(self):
        return sorted(
            glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
            )
        )

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in self._sdk_llvm_lib_dirs():
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # The sandbox LD_LIBRARY_PATH carries an incompatible
            # libc++_shared.so which shadows the compatible one; prepend
            # /system/lib64 so the loader resolves the compatible libc++
            # first (kconfig 6.26.0 / kcodecs 6.26.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if not dep or not dep.package_folder:
                continue
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
            )
            runtime_env.prepend_path(
                "PATH", os.path.join(dep.package_folder, "bin")
            )
            runtime_env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
            )
            runtime_env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
            )
        # Highest priority for the Qt6 build that actually has Sql, and for
        # the build-tree library itself.
        qt = self.dependencies.get("qtbase-sql-dbus")
        if qt and qt.package_folder:
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(qt.package_folder, "lib")
            )
            runtime_env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(qt.package_folder, "plugins")
            )
        for rel in ("bin", "lib", "src", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        runtime_env.define("QT_QPA_PLATFORM", "offscreen")
        return runtime_env

    def _run_upstream_tests(self):
        if not can_run(self):
            return
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own FutureSQL6Config.cmake with proper
        # dependency tracking (find_dependency on Qt6Core/Qt6Sql). Use
        # cmake_find_mode=none so CMakeDeps does not shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["futuresql6"]
