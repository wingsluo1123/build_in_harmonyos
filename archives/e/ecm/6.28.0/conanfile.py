#!/usr/bin/env python3
"""Conan recipe for ECM 6.28.0 on HarmonyOS PC (aarch64).

ECM (Extra CMake Modules) is a collection of additional CMake modules from KDE.
It is a pure CMake module library — no binary code is compiled or linked.

OHOS-specific adaptations:
  - No patches required; ECM installs cleanly on HarmonyOS.
  - package_type = "build-scripts": ECM ships only CMake modules.
  - package_id() uses self.info.clear() to avoid package ID variations
    from compiler/build_type settings (no compiled artifacts).
  - BUILD_TESTING=OFF to skip upstream tests during build (tests are
    optional, Qt-dependent; the module set itself has no runtime deps).
  - The HNP cmake binary dynamically loads libc++_shared.so from the SDK
    aarch64-linux-ohos lib dir; prepend it to LD_LIBRARY_PATH so cmake can
    start (same pattern as prison 6.18.0 _library_runtime_env).
"""
import glob
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ECMConan(ConanFile):
    name = "ecm"
    version = "6.28.0"
    description = "Extra CMake Modules - additional CMake modules from KDE"
    license = "BSD-3-Clause"
    homepage = "https://kde.org/products/frameworks/"
    url = "https://invent.kde.org/frameworks/extra-cmake-modules"

    package_type = "build-scripts"

    settings = "os", "compiler", "build_type", "arch"

    def package_id(self):
        self.info.clear()

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()
        # Persist the SDK runtime env as a buildenv script so it also covers
        # the package() install step (cmake --install invokes the HNP cmake
        # binary which needs libc++_shared.so from the SDK lib dir).
        self._sdk_runtime_env().vars(self).save_script("sdk_runtime_env")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

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

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ECM")
        self.cpp_info.set_property("cmake_target_name", "ECM::ECM")
        self.cpp_info.builddirs = ["share/ECM/cmake"]
