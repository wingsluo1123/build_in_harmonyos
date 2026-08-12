#!/usr/bin/env python3
import os
from conan import ConanFile


class BackwardCppTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def test(self):
        bw = self.dependencies["backward-cpp"]
        bw_inc = os.path.join(bw.package_folder, "include")
        bw_lib = os.path.join(bw.package_folder, "lib")
        src = os.path.join(self.source_folder, "src", "test_backward.cpp")
        test_bin = os.path.join(self.build_folder, "test_backward")
        # -std=c++11：backward.hpp 需要 C++11（stacktrace API）
        self.run(
            f"${{CXX:-clang++}} ${{CXXFLAGS}} -std=c++11 -o \"{test_bin}\" \"{src}\" "
            f"-I{bw_inc} -L{bw_lib} -lbackward",
            env="conanbuild",
        )
        self.run(f'"{test_bin}"', env="conanrun")
