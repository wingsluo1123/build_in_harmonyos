#!/usr/bin/env python3
"""Conan test_package for knewstuff5 5.116.0 (KDE Frameworks 5 line).

Builds and runs a consumer that exercises the real KNSCore API
(EntryInternal / Author / Engine) exported by libKF5NewStuffCore.

Runtime execution uses a materialised, freshly self-signed library view -
same OHOS loader constraints documented in the main recipe (E505 versioned
soname alias resolution; E212 untrusted package self-sign data).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get


class KNewStuff5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    _SIGN_TOOL = "/data/service/hnp/bin/binary-sign-tool"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # qtbase for Qt5Core/Gui/Xml in the KF5NewStuffCore config
        # find_dependency chain; qtdeclarative is linked by the packaged
        # lib and must resolve transitively at build and runtime.
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("qt5-qtdeclarative/5.15.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # All KF5/Qt packages use cmake_find_mode=none; CMakeDeps does not
        # add their own lib/cmake dirs to the search paths. Wire every
        # dependency package folder explicitly so the upstream config files
        # (KF5NewStuffCoreConfig + its find_dependency chain) resolve.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if not (dep and dep.package_folder):
                continue
            pkg = os.fspath(dep.package_folder).replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        mirror = self._build_runtime_mirror()
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.prepend_path("LD_LIBRARY_PATH", mirror)
        env.define("QT_QPA_PLATFORM", "offscreen")
        home = os.path.join(self.build_folder, "test-home")
        xdg = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(home, exist_ok=True)
        os.makedirs(xdg, exist_ok=True)
        os.chmod(xdg, 0o700)
        env.define("HOME", home)
        env.define("XDG_RUNTIME_DIR", xdg)
        env.define("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(home, ".local", "share"))
        with env.vars(self).apply():
            self.run(
                'ctest --test-dir "{0}" --output-on-failure'.format(
                    self.build_folder
                )
            )

    def _build_runtime_mirror(self):
        mirror = os.path.join(self.build_folder, "runtime-mirror")
        if os.path.isdir(mirror):
            shutil.rmtree(mirror)
        os.makedirs(mirror)

        entries = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                entries.extend(glob.glob(os.path.join(libdir, "*.so")))
                entries.extend(glob.glob(os.path.join(libdir, "*.so.[0-9]*")))

        copied = set()
        for src in entries:
            name = os.path.basename(src)
            if name in copied:
                continue
            real = os.path.realpath(src)
            if not (real and os.path.isfile(real)):
                continue
            shutil.copyfile(real, os.path.join(mirror, name))
            shutil.copymode(real, os.path.join(mirror, name))
            copied.add(name)

        if not copied:
            raise RuntimeError("test_package runtime-mirror collected no libs")

        for name in copied:
            path = os.path.join(mirror, name)
            tmp = os.path.join(mirror, ".tmp-signed")
            self.run(
                '"{0}" sign -selfSign 1 -inFile "{1}" -outFile "{2}" '
                "-signAlg SHA256withECDSA".format(self._SIGN_TOOL, path, tmp),
                quiet=True,
            )
            with open(tmp, "rb") as src_f, open(path, "wb") as dst_f:
                shutil.copyfileobj(src_f, dst_f)
            os.remove(tmp)

        return mirror
