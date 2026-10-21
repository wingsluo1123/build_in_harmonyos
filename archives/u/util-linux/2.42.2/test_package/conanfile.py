#!/usr/bin/env python3
"""Conan test_package for util-linux 2.42.2.

编译消费者程序，真实调用三个交付库的 API（libblkid / libuuid / libmount）。
链接顺序取自被测包 package_info 的 cpp_info.libs，因此同时验证声明的链接顺序
（libmount → libblkid → libuuid，静态库被依赖者靠后）是否正确。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class UtilLinuxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies[self.tested_reference_str]
        incs = dep.cpp_info.includedirs
        libdirs = dep.cpp_info.libdirs
        libs = dep.cpp_info.libs
        if not libs:
            raise ConanException("util-linux package_info.libs 为空，无法验证链接")

        inc_flags = " ".join("-I" + p for p in dict.fromkeys(incs))
        link_flags = " ".join(["-L" + p for p in dict.fromkeys(libdirs)]
                              + ["-l" + name for name in libs]
                              + ["-Wl,-rpath," + p for p in dict.fromkeys(libdirs)])
        self.output.info(f"consumer links (package_info order): {libs}")

        cc = os.environ.get("CXX") or "clang++"
        if not shutil.which(cc):
            cc = "clang++"
        self.run(f"{cc} -std=c++17 test_util_linux.cpp -o test_util_linux_probe "
                 f"{inc_flags} {link_flags}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile+link verified, runtime probe skipped")
            return
        self.run("./test_util_linux_probe", env="conanrun")
