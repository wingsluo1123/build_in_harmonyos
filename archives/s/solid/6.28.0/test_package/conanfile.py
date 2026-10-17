#!/usr/bin/env python3
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class SolidTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")',
                    ]
                )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        with open(os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _stage_runtime_libraries(self):
        runtime_dirs = {self.build_folder, self.cpp.build.bindirs[0]}
        for runtime_dir in runtime_dirs:
            os.makedirs(runtime_dir, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib") if dep.package_folder else None
            if not libdir or not os.path.isdir(libdir):
                continue
            for name in os.listdir(libdir):
                if not (name.startswith("lib") and ".so" in name):
                    continue
                source = os.path.realpath(os.path.join(libdir, name))
                for runtime_dir in runtime_dirs:
                    link = os.path.join(runtime_dir, name)
                    if os.path.realpath(link) == source:
                        continue
                    if os.path.lexists(link):
                        if self._is_same_file_copy(link, source):
                            continue
                        os.unlink(link)
                    try:
                        os.symlink(source, link)
                    except OSError:
                        # HMDFS 拒 symlink（EPERM）与硬链接（EPERM）→
                        # 物化为普通拷贝，$ORIGIN 运行期契约仍可解析
                        # （qzxing/kpeople 6.28.0 先例）。
                        shutil.copy2(source, link)

    @staticmethod
    def _is_same_file_copy(dst, target):
        """True when dst is already a plain copy of target (copy2 keeps mtime)."""
        if os.path.islink(dst) or not os.path.isfile(dst):
            return False
        try:
            return (
                os.path.getsize(dst) == os.path.getsize(target)
                and int(os.path.getmtime(dst)) == int(os.path.getmtime(target))
            )
        except OSError:
            return False

    def test(self):
        self._stage_runtime_libraries()
        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_solid"), env="conanrun")
