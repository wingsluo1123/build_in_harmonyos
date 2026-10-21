#!/usr/bin/env python3
"""Conan recipe for Breeze Icons (breeze-icons5) 5.116.0 on HarmonyOS PC.

Breeze is the default icon theme of the KDE Plasma desktop.  This recipe
builds the theme with upstream CMake (data install) AND runs the upstream
autotests (symlink / newline / dupe / scalable), so the declared test counts
reflect a real run.

OHOS adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE; manual ECM_MODULE_PATH; OHOS SONAME flag.
  - BUILD_TESTING=ON: upstream autotests are QtTest programs linking Qt5::Test
    and reading the source icon tree; they are executed offscreen via ctest.
  - BINARY_ICONS_RESOURCE=OFF: qrcAlias is a native host tool that cannot be
    executed while cross-compiling to OHOS, and the .rcc is not required by
    consumers at build time.
  - WITH_ICON_GENERATION=OFF: the optional 24px monochrome variants are
    generated via python3-lxml on the build host, which is not guaranteed.
  - Data payload identical to the upstream CMake install rules
    (share/icons/breeze + share/icons/breeze-dark, incl. the light-icon
    fallback into breeze-dark and each theme's index.theme).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get


class BreezeIconsConan(ConanFile):
    name = "breeze-icons5"
    version = "5.116.0"
    description = "Breeze icon theme for KDE Frameworks 5"
    license = "LGPL-3.0-or-later"
    homepage = "https://invent.kde.org/frameworks/breeze-icons"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")
        # Upstream autotests (dupe) invoke the `fdupes` binary; provide it so
        # every upstream CTest case really runs on OHOS.
        self.tool_requires("fdupes/2.4.0")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        # Breeze-specific: keep the optional host-only features off.
        tc.variables["BINARY_ICONS_RESOURCE"] = "OFF"
        tc.variables["WITH_ICON_GENERATION"] = "OFF"
        tc.cache_variables["QT_MAJOR_VERSION"] = "5"
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
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [f"{ecm_share}/modules", f"{ecm_share}/find-modules", f"{ecm_share}/kde-modules"]
            )

        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase:
            self._prepare_qt_mkspec_compat(qtbase.package_folder)
        lines = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")')
        if ecm:
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm.package_folder}/share/ECM/cmake")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm.package_folder}/share/ECM/cmake")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        with open(os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w") as f:
            f.write("\n".join(lines) + "\n")
        tc.generate()

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

    def _runtime_env(self):
        env = Environment()
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        with self._runtime_env().vars(self).apply():
            cmake.build()
            self.run(f'ctest --test-dir "{self.build_folder}" --output-on-failure --no-tests=error')

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # Upstream CMake does not install the license files; keep shipping
        # them under share/licenses as in the original data-only recipe.
        src = self.source_folder
        lic_dst = os.path.join(self.package_folder, "share", "licenses", self.name)
        for rel in ("COPYING-ICONS", "COPYING.LIB"):
            if os.path.isfile(os.path.join(src, rel)):
                copy(self, rel, src=src, dst=lic_dst)
        for theme in ("icons", "icons-dark"):
            theme_dir = os.path.join(src, theme)
            if os.path.isfile(os.path.join(theme_dir, "LICENSE")):
                copy(self, "LICENSE", src=theme_dir, dst=lic_dst)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
