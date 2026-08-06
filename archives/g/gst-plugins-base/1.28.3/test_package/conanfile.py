import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        lib_flags = " ".join([f"-L{d}" for d in libdirs])
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test_base.c -o test_probe {inc} {lib_flags} -lgstreamer-1.0 -lgstaudio-1.0 -ldl")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile+link only")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
