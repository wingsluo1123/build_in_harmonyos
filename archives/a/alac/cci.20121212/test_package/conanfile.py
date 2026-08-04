#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import save


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Get compiler from conf
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            cxx = compilers.get("cpp", "clang++")
            # Get package info from dependency
            dep = self.dependencies["alac"]
            include_dir = os.path.join(dep.package_folder, "include")
            lib_dir = os.path.join(dep.package_folder, "lib")

            # Write test source
            test_src = '''#include <cstdio>
#include "ALACEncoder.h"
#include "ALACDecoder.h"

int main() {
    ALACEncoder encoder;
    ALACDecoder decoder;
    ALACSpecificConfig config;
    encoder.GetConfig(config);
    uint32_t cookieSize = encoder.GetMagicCookieSize(2);
    printf("ALAC test passed! frameLength=%u\\n", (unsigned)config.frameLength);
    return 0;
}
'''
            build_dir = os.path.join(self.build_folder, "test_build")
            os.makedirs(build_dir, exist_ok=True)
            src_path = os.path.join(build_dir, "test_package.cpp")
            bin_path = os.path.join(build_dir, "test_package")
            save(self, src_path, test_src)
            self.run(f"{cxx} -I{include_dir} -L{lib_dir} {src_path} -lalac -lm -o {bin_path}")
            self.run(bin_path, env="conanrun")