#!/usr/bin/env python3
"""Conan test_package for kxmlgui 6.28.0.

Verifies that the KF6XmlGui library can be found via CMake and that
the KXmlGuiWindow API is callable (R34: real API usage). The bundled
executor drives the public window/action/toolbar APIs and reports each
case independently.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KxmlguiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        # Mirror the kxmlgui 6.28.0 dependency matrix: KF6 6.26 line with
        # kconfigwidgets pinned at the published 6.18.0 cap and its
        # transitive deps overridden to the 6.26 line (single override
        # declarations; a duplicated plain requires is rejected by conan).
        self.requires("kiconthemes/6.26.0")
        self.requires("kitemviews/6.26.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("kguiaddons/6.26.0", override=True)
        self.requires("ki18n/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        self.requires("kcolorscheme/6.26.0", override=True)
        self.requires("kcodecs/6.26.0", override=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(
            self.tested_reference_str.split("/")[0]
        )
        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{qt_pkg}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")'
            )
        # Expose all KF6/Qt6 deps so find_dependency() chains resolve.
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
        lines.append(
            f'list(PREPEND CMAKE_PREFIX_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # KF6 libraries record build-tree-relative DT_NEEDED entries; mirror
        # the expected layout under test_package/bin by symlinking every KF6
        # shared library there.
        tp_bin = os.path.join(self.build_folder, "..", "..", "bin")
        os.makedirs(tp_bin, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib") if dep.package_folder else None
            if libdir and os.path.isdir(libdir):
                for name in os.listdir(libdir):
                    if name.startswith("libKF6") and name.endswith(".so"):
                        link = os.path.join(tp_bin, name)
                        if not os.path.lexists(link):
                            try:
                                os.symlink(os.path.join(libdir, name), link)
                            except OSError:
                                # HMDFS rejects symlink(); fall back to a copy.
                                shutil.copy2(os.path.join(libdir, name), link)

        env = Environment()
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        # Sandbox libc++_shared.so shadowing (kconfig 6.26.0 precedent).
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # KXmlGuiWindow creates QWidgets; run headless (xcb is not available).
        env.define("QT_QPA_PLATFORM", "offscreen")
        # Fresh KConfig/XDG state, mirroring the upstream test harness: a
        # previously used test-home can flip locale-dependent results. This
        # also keeps repeated `conan test` invocations independent of each
        # other and of the upstream ctest run.
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        with env.vars(self).apply():
            # Single execution path: the in-source CMakeLists.txt registers
            # the same binary via add_test(), but `cmake.test()` would run it
            # without this environment and the second execution would see
            # the first one's KConfig state.
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kxmlgui"),
                env="conanrun",
            )
