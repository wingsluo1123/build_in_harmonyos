#!/usr/bin/env python3
"""Conan recipe for KIdleTime (kidletime5) 5.116.0 on HarmonyOS PC.

KIdleTime is the KDE Frameworks library that reports the user's idle time.

OHOS-specific adaptations (same family reuse as kconfig5 / kwidgetsaddons5):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in KDE's platform list).
  - X11 and Wayland pollers are absent on OHOS: find_package(X11) fails and
    Qt5WaylandClient is not shipped by qt5-qtbase, so no OS poller plugin is
    built; the library ships its platform-independent core, which is the same
    code path upstream uses on unsupported platforms.
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project relies on.
  - conan_cmakedeps_paths.cmake created manually because qtbase is published
    with cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH.
  - OHOS CMake platform module does not define the SONAME flag; set
    CMAKE_SHARED_LIBRARY_SONAME_* to "-Wl,-soname," so KF5 .so get a real
    DT_SONAME and consumers record the bare name (avoiding the E537
    path-form DT_NEEDED loader failure).
  - Dependencies: qt5-qtbase/5.15.2.2 (Qt5Core/Qt5Gui) and ecm/6.20.0.
  - No upstream autotests exist for KIdleTime, so no ctest step is run.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, load, save


class Kidletime5Conan(ConanFile):
    name = "kidletime5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - user idle time reporting (KIdleTime)"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/frameworks/kidletime"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"

        if str(self.settings.os) in ("Linux", "OHOS"):
            if str(self.settings.os) == "OHOS":
                tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
                tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            targets = {"armv8": "aarch64-linux-ohos", "x86_64": "x86_64-linux-ohos"}
            target = targets.get(str(self.settings.arch))
            if target:
                tc.variables["CMAKE_C_COMPILER_TARGET"] = target
                tc.variables["CMAKE_CXX_COMPILER_TARGET"] = target

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = self._cmake_path(os.path.join(ecm.package_folder, "share", "ECM"))
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [f"{ecm_share}/modules", f"{ecm_share}/find-modules", f"{ecm_share}/kde-modules"]
            )

        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase:
            self._prepare_qt_mkspec_compat(qtbase.package_folder)
            qt_pkg = self._cmake_path(qtbase.package_folder)
            lines = [
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")',
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")',
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")',
            ]
            if ecm:
                ecm_pkg = self._cmake_path(ecm.package_folder)
                ecm_cmake = f"{ecm_pkg}/share/ECM/cmake"
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    @staticmethod
    def _cmake_path(path):
        return os.fspath(path).replace("\\", "/")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        src_mkspecs = os.path.join(qt_package_folder, "mkspecs")
        dst_mkspecs = os.path.join(os.path.dirname(qt_package_folder), "b", "mkspecs")
        if os.path.isdir(src_mkspecs):
            for rel in ("linux-clang", "common"):
                src = os.path.join(src_mkspecs, rel)
                dst = os.path.join(dst_mkspecs, rel)
                if os.path.isdir(src) and not os.path.islink(dst) and not os.path.isdir(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copytree(src, dst)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._make_pkgconfig_relocatable()

    def _make_pkgconfig_relocatable(self):
        package_root = self._cmake_path(self.package_folder).rstrip("/")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        for pc_file in glob.glob(os.path.join(pc_dir, "*.pc")):
            content = load(self, pc_file)
            content = content.replace(f"prefix={package_root}", "prefix=${pcfiledir}/../..", 1)
            content = content.replace(f"libdir={package_root}/lib", "libdir=${prefix}/lib", 1)
            content = content.replace(f"includedir={package_root}/include", "includedir=${prefix}/include", 1)
            content = content.replace(f"-L{package_root}/lib", "-L${libdir}")
            content = content.replace(f"-I{package_root}/include", "-I${includedir}")
            save(self, pc_file, content)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5IdleTime"]
