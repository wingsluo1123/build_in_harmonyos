#!/usr/bin/env python3
"""Conan test_package for prison 6.28.0.

Consumer smoke test: create a QRCode barcode through KF6::Prison,
render it to a QImage and assert the image is non-null.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class PrisonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("qtmultimedia/6.11.1")
        self.requires("qrencode/4.1.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()
        self._write_cmake_paths()
        # HNP cmake binary needs libc++_shared.so from the SDK
        # aarch64-linux-ohos dir; persist the runtime env so the
        # configure/build/test steps can start cmake and run the binary.
        self._sdk_runtime_env().vars(self).save_script("sdk_runtime_env")

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
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _sdk_runtime_env(self):
        env = Environment()
        sdk_base = os.environ.get("OHOS_SDK_HOME", "/data/service/hnp/ohos-sdk.org")
        sdk_libs = sorted(
            glob.glob(os.path.join(sdk_base, "*", "ohos", "native", "llvm", "lib"))
        )
        for lib_dir in sdk_libs:
            env.prepend_path("LD_LIBRARY_PATH", lib_dir)
            sub = os.path.join(lib_dir, "aarch64-linux-ohos")
            if os.path.isdir(sub):
                env.prepend_path("LD_LIBRARY_PATH", sub)
        return env

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._prepare_runtime_links()
        env = Environment()
        runtime_dirs = [
            self.cpp.build.bindirs[0],
            os.path.normpath(os.path.join(self.build_folder, "..", "..", "bin")),
        ]
        for runtime_dir in runtime_dirs:
            env.prepend_path("LD_LIBRARY_PATH", runtime_dir)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_prison")
        with self._sdk_runtime_env().vars(self).apply():
            with env.vars(self).apply():
                self.run(test_exe, cwd=self.cpp.build.bindirs[0])

    def _prepare_runtime_links(self):
        runtime_dirs = [
            self.cpp.build.bindirs[0],
            os.path.normpath(os.path.join(self.build_folder, "..", "..", "bin")),
        ]
        for runtime_dir in runtime_dirs:
            os.makedirs(runtime_dir, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib") if dep.package_folder else None
            if not libdir or not os.path.isdir(libdir):
                continue
            for src in glob.glob(os.path.join(libdir, "lib*.so*")):
                for runtime_dir in runtime_dirs:
                    dst = os.path.join(runtime_dir, os.path.basename(src))
                    if os.path.exists(dst):
                        continue
                    shutil.copy2(src, dst)
