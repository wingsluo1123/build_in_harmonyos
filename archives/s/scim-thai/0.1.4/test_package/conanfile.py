#!/usr/bin/env python3
"""Conan test_package for scim-thai — consumer smoke test.

scim-thai builds a SCIM IMEngine module (thai.so), not a conventional
linked library, so the consumer test dlopens the installed module and
verifies the SCIM factory symbol is exported (direct clang++ + dlopen;
no CMake — the HNP cmake binary cannot load libc++_shared.so inside the
conan subprocess environment, same pattern as scim/libthai).
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv / VirtualBuildEnv so the probe gets the run-time
    # LD_LIBRARY_PATH of all dependencies when executed.
    generators = "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _all_libdirs(self):
        libdirs = []
        for _ref, dep in self.dependencies.items():
            libdirs += dep.cpp_info.libdirs
        return list(dict.fromkeys(libdirs))

    def _find_module(self):
        """Locate the installed thai.so module under the package folder."""
        pkg = self.dependencies["scim-thai"].package_folder
        for root, _dirs, files in os.walk(pkg):
            if "thai.so" in files:
                return os.path.join(root, "thai.so")
        return None

    def build(self):
        if not self._find_module():
            self.output.error("thai.so module not found under package folder")
            raise SystemExit(1)
        cxx = os.environ.get("CXX", "clang++")
        self.run(f"{cxx} -std=gnu++17 test.cpp -o test_probe -ldl")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only compile+link")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        libdirs = self._all_libdirs()
        if str(self.settings.os) == "OHOS":
            tools = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
            compiler = tools.get("c", "clang")
            real_clang = os.path.realpath(compiler)
            llvm_lib = os.path.join(
                os.path.dirname(os.path.dirname(real_clang)), "lib",
                "aarch64-linux-ohos")
            if os.path.isdir(llvm_lib):
                libdirs = list(dict.fromkeys(libdirs + [llvm_lib]))
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        module = self._find_module()
        if not module:
            self.output.error("thai.so module not found under package folder")
            raise SystemExit(1)
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; "
            f"./test_probe \"{module}\"'",
            env="conanrun")
