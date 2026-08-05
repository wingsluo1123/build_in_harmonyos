#!/usr/bin/env python3
"""Consumer smoke test for gcc12."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.layout import basic_layout


class Gcc12TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    @staticmethod
    def _ohos_sysroot(cc):
        if not cc or not os.path.isabs(str(cc)):
            raise ConanInvalidConfiguration(
                "OHOS test_package requires an absolute compiler path in "
                "tools.build:compiler_executables to derive the sysroot"
            )
        return os.path.normpath(
            os.path.join(os.path.dirname(str(cc)), "..", "sysroot")
        )

    def test(self):
        package = self.dependencies["gcc12"]
        bindir = os.path.join(package.package_folder, package.cpp_info.bindirs[0])
        gcc = os.path.join(bindir, "gcc")
        gxx = os.path.join(bindir, "g++")
        compile_flags = ""
        link_flags = ""
        if self.settings.os == "OHOS":
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            cc = compilers.get("c") or compilers.get("cpp") or compilers.get("cxx")
            sysroot = self._ohos_sysroot(cc)
            target_include = os.path.join(
                sysroot, "usr", "include", "aarch64-linux-ohos"
            )
            libdir = os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos")
            availability_header = os.path.join(
                package.package_folder,
                "include",
                "gcc12-ohos",
                "ohos-availability.h",
            )
            compile_flags = (
                f" --sysroot={shlex.quote(sysroot)}"
                f" -include {shlex.quote(availability_header)}"
                f" -isystem {shlex.quote(target_include)}"
            )
            link_flags = (
                f" -B{shlex.quote(libdir)}/"
                f" -L{shlex.quote(libdir)}"
                f" -Wl,-rpath-link,{shlex.quote(libdir)}"
                " -Wl,--code-sign"
            )
        c_src = os.path.join(self.source_folder, "test.c")
        c_bin = os.path.join(self.build_folder, "gcc12_c_smoke")

        self.run(f"{shlex.quote(gcc)} --version", env="conanrun")
        self.run(
            f"{shlex.quote(gcc)} {shlex.quote(c_src)} -o {shlex.quote(c_bin)}"
            f"{compile_flags}{link_flags}",
            env="conanrun",
        )
        self.run(shlex.quote(c_bin), env="conanrun")

        if os.path.exists(gxx):
            cxx_src = os.path.join(self.source_folder, "test.cpp")
            cxx_bin = os.path.join(self.build_folder, "gcc12_cxx_smoke")
            self.run(
                f"{shlex.quote(gxx)} {shlex.quote(cxx_src)} -o {shlex.quote(cxx_bin)}"
                f"{compile_flags}{link_flags}",
                env="conanrun",
            )
            self.run(shlex.quote(cxx_bin), env="conanrun")
