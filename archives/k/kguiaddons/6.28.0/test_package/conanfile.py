#!/usr/bin/env python3
"""Conan test_package for kguiaddons 6.28.0."""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KguiaddonsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            # The package ships its own KF6GuiAddonsConfig.cmake
            # (cmake_find_mode=none); point CMake at its lib/cmake.
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{pkg.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
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
        tp_bin = os.path.join(self.build_folder, "..", "..", "bin")
        os.makedirs(tp_bin, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib") if dep.package_folder else None
            if libdir and os.path.isdir(libdir):
                for name in os.listdir(libdir):
                    if name.startswith("libKF6") and name.endswith(".so"):
                        link = os.path.join(tp_bin, name)
                        if not os.path.lexists(link):
                            # HMDFS rejects symlink() with EPERM device-wide;
                            # fall back to a plain copy (the libs are also on
                            # LD_LIBRARY_PATH, this dir is belt-and-braces
                            # for slash-containing DT_NEEDED entries).
                            try:
                                os.symlink(os.path.join(libdir, name), link)
                            except OSError:
                                shutil.copy2(os.path.join(libdir, name), link)

        env = Environment()
        env.append(
            "LD_LIBRARY_PATH",
            [
                os.path.join(p.package_folder, "lib")
                for p in self.dependencies.values()
                if p.package_folder
            ],
        )
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # The consumer cases create a QGuiApplication (icon/pixmap rendering);
        # no display is available on OHOS workers, so force the offscreen
        # platform plugin and isolate HOME/XDG under the build folder (the
        # OHOS sandbox does not provide a writable user profile).
        env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(test_home, "runtime")
        for directory in (test_home, xdg_runtime):
            os.makedirs(directory, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(test_home, "cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(test_home, "config"))
        env.define("XDG_DATA_HOME", os.path.join(test_home, "data"))
        with env.vars(self).apply():
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kguiaddons"),
                env="conanrun",
            )
