import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["gstreamer"].cpp_info
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0] if dep.libdirs else ""
        so = os.path.join(libdir, "libgstreamer-1.0.so") if libdir else "libgstreamer-1.0.so"
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test_gstreamer.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' -ldl")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile+link only")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
