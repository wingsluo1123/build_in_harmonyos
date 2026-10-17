#!/usr/bin/env python3
"""Conan recipe for kded (kded5) 5.116.0 on HarmonyOS PC.

kded5 is the KDE Frameworks daemon (the KDE Daemon) that loads KDED modules
and provides on-demand background services.  It builds a single executable
(bin/kded5) plus its data (D-Bus interface/service, systemd user unit, kded
module desktop file) — it produces no library.

OHOS-specific adaptations (same family reuse as kconfig5/kidletime5):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection.
  - ECM_MODULE_PATH set manually (CMakeDeps ECMConfig.cmake does not propagate).
  - conan_cmakedeps_paths.cmake written by hand: every KF5 dependency is
    published with cmake_find_mode=none, so CMakeDeps does not add its
    lib/cmake builddir to CMAKE_PREFIX_PATH; we prepend each dependency's
    lib/cmake (and qtbase's) explicitly.
  - OHOS CMake platform module lacks the SONAME flag; set
    CMAKE_SHARED_LIBRARY_SONAME_* for real DT_SONAME (avoids E537).
  - KF5DocTools is left optional (find_package(KF5DocTools) is not REQUIRED);
    not pulling it keeps the dependency set minimal and skips po/doc
    installation.
  - Dependencies: qt5-qtbase/5.15.2.2, kconfig5, kcoreaddons5, kcrash5,
    kdbusaddons5, kservice5 (all 5.116.0), ecm/6.20.0 for the build.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, load, save


class Kded5Conan(ConanFile):
    name = "kded5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - the KDE daemon (KDED)"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/frameworks/kded"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # The published KF5 stack is split on qt5-qtbase: kcoreaddons5/5.116.0
        # pins 5.15.2 while kconfig5/kservice5/kdbusaddons5/kcrash5 all pin
        # 5.15.2.2. kded5 needs both, so force one version (5.15.2.2, the
        # majority) via override; kcoreaddons5 is (re)built from its recipe if
        # no 5.15.2.2 binary is published.
        self.requires("qt5-qtbase/5.15.2.2", override=True)
        self.requires("kconfig5/5.116.0")
        # The published KF5 stack also disagrees on kcoreaddons5: kcrash5 pins
        # 5.116.0 while kservice5 pins 5.116.0.1. Force a single version
        # (5.116.0.1) so the graph resolves; kcrash5 is rebuilt from its recipe
        # if needed.
        self.requires("kcoreaddons5/5.116.0.1", override=True)
        self.requires("kcrash5/5.116.0")
        self.requires("kdbusaddons5/5.116.0")
        self.requires("kservice5/5.116.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
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

        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        # Prepend every dependency's CMake/config dirs (all KF5 packages use
        # cmake_find_mode=none, so CMakeDeps does not add them for us).
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            p = self._cmake_path(dep.package_folder)
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{p}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{p}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{p}/include")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{p}")')
        if ecm:
            ecm_pkg = self._cmake_path(ecm.package_folder)
            ecm_cmake = f"{ecm_pkg}/share/ECM/cmake"
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        if qtbase:
            qt_pkg = self._cmake_path(qtbase.package_folder)
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
        with open(os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w") as f:
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
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
