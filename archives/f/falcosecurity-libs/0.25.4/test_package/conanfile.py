#!/usr/bin/env python3
"""Conan consumer test for falcosecurity-libs."""

import json
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class FalcoSecurityLibsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # DT_NEEDED in libsinsp.so/libscap.so uses build-relative paths
        # (e.g. ../jsoncpp-prefix/src/lib/libjsoncpp.so) which don't resolve
        # at runtime. Set LD_LIBRARY_PATH to find installed bundled deps,
        # engine shared libraries, and OHOS C++ runtime from the NDK.
        dep = self.dependencies["falcosecurity-libs"]
        lib_dir = os.path.join(dep.package_folder, "lib")
        bundled_dir = os.path.join(lib_dir, "falcosecurity")
        # Resolve OHOS C++ runtime lib dir via the cross-compiler (from profile)
        _cc_info = self.conf.get("tools.build:compiler_executables", {})
        if isinstance(_cc_info, str):
            _cc_info = json.loads(_cc_info)
        _cc_path = os.path.join(
            os.path.dirname(_cc_info.get("c", "")),
            "aarch64-unknown-linux-ohos-clang"
        )
        _ohos_lib_dir = ""
        if os.path.exists(_cc_path):
            _ohos_lib_dir = os.path.dirname(
                subprocess.check_output(
                    [_cc_path, "-print-file-name=libc++_shared.so"],
                    text=True
                ).strip()
            )
        ld_path = f"{lib_dir}:{bundled_dir}:{_ohos_lib_dir}" if _ohos_lib_dir else f"{lib_dir}:{bundled_dir}"
        self.run(
            f"LD_LIBRARY_PATH={ld_path} ./test_falcosecurity_libs",
            env="conanrun",
        )
