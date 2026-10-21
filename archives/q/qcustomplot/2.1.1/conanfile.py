#!/usr/bin/env python3
"""Conan 2 recipe for QCustomPlot 2.1.1 on HarmonyOS PC.

QCustomPlot is a single-translation-unit Qt widget library (qcustomplot.cpp /
qcustomplot.h) for plotting and data visualization. Upstream publishes the
two sources plus the licence and changelog only: there is no build system and
no test suite. This recipe supplies a CMake build that installs
libQCustomPlot.so, the public header and a relocatable CMake package
(QCustomPlotConfig.cmake, target QCustomPlot::QCustomPlot).

OHOS adaptations:
  - qtbase/6.11.1 in this repository is built with FEATURE_printsupport=OFF
    and ships no Qt6PrintSupport module. QCustomPlot's only PrintSupport use
    is QCustomPlot::savePdf, whose implementation upstream already guards
    with QT_NO_PRINTER. The header include gets the same guard (patch 0001)
    and CMakeLists.txt probes the module with
    find_package(Qt6 OPTIONAL_COMPONENTS PrintSupport): when it is missing the
    target defines QT_NO_PRINTER and savePdf becomes the upstream
    "printer support unavailable" stub. Capability probe only, no platform
    macro (R8).
  - qtbase sets cmake_find_mode=none, so CMakeDeps emits no Qt config;
    conan_cmakedeps_paths.cmake is written here to point CMake at the real
    Qt6Config.cmake and at the Qt package lib/include dirs (futuresql/kmag
    precedent).
  - HMDFS refuses symlink(2): a runtime probe sets
    CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON and CMake is given the Linux SONAME
    flag, so the installed library is a single libQCustomPlot.so that still
    carries DT_SONAME (E330 family).
"""
import errno
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class QcustomplotConan(ConanFile):
    name = "qcustomplot"
    version = "2.1.1"
    description = "QCustomPlot - Qt widget for plotting and data visualization"
    license = "GPL-3.0-only"
    homepage = "https://www.qcustomplot.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)
        copy(self, "cmake/*", self.recipe_folder, self.export_sources_folder)
        export_conandata_patches(self)

    def requirements(self):
        # QCustomPlot public headers expose QtWidgets/QtGui/QtCore types, so
        # the Qt dependency is part of the consumer ABI.
        self.requires("qtbase/6.11.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _symlinks_supported(self):
        """Probe symlink(2) support in the generators folder.

        CMake creates the VERSION/SOVERSION symlink chain at link time; on
        HMDFS that call fails with EACCES/EPERM and aborts the build. Detect
        the capability at generate() time instead of branching on a platform
        macro (DRAFT-7341 libtiff precedent). Only file-system refusals are
        treated as "no symlinks"; unrelated I/O errors propagate.
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
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QCUSTOMPLOT_VERSION"] = str(self.version)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = (
            "ON" if self.options.get_safe("fPIC", True) else "OFF"
        )
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        if str(self.settings.os) == "OHOS":
            # OHOS CMake uses the Generic platform module, which has no
            # shared-library soname rule. Inject the Linux-style flag so the
            # installed library records DT_SONAME (L5a/L5c).
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            if self.options.shared and not self._symlinks_supported():
                # HMDFS rejects symlink(2), so CMake's versioned .so chain
                # cannot be created. Keep the bare SONAME (injected above) and
                # skip the versioned names (DRAFT-7341 libtiff precedent).
                tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"

        qt = self.dependencies.get("qtbase")
        if qt and qt.package_folder:
            tc.variables["Qt6_DIR"] = os.path.join(
                qt.package_folder, "lib", "cmake", "Qt6"
            )
        self._write_cmake_paths(qt)
        tc.generate()

    def _write_cmake_paths(self, qt):
        """Write conan_cmakedeps_paths.cmake (auto-included by the toolchain).

        CMakeDeps generates no config for packages with cmake_find_mode=none,
        so their builddirs are missing from CMAKE_PREFIX_PATH. Add them here,
        keeping qtbase ahead of everything else.
        """
        prefixes = []
        libraries = []
        includes = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized and normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if not dep or not dep.package_folder:
                continue
            add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
            add_unique(prefixes, dep.package_folder)
            add_unique(libraries, os.path.join(dep.package_folder, "lib"))
            add_unique(includes, os.path.join(dep.package_folder, "include"))

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
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

    def _build_env(self):
        build_env = Environment()
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if not dep or not dep.package_folder:
                continue
            build_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
            )
            build_env.prepend_path(
                "PATH", os.path.join(dep.package_folder, "bin")
            )
        if str(self.settings.os) == "OHOS":
            # The sandbox LD_LIBRARY_PATH may carry a libc++_shared.so that is
            # incompatible with the SDK one; /system/lib64 goes ahead of it.
            # Prepended before the dependency dirs on purpose: each
            # prepend_path puts the entry at the front, so the package lib
            # dirs still win when the same library name exists in both.
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "GPL.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "changelog.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # The project installs its own QCustomPlotConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Core/Qt6Gui/Qt6Widgets).
        # Use cmake_find_mode=none so CMakeDeps does not shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["QCustomPlot"]
