import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["sdl2_ttf"].cpp_info
        inc = " ".join("-I" + d for d in dep.includedirs)
        libdir = dep.libdirs[0] if dep.libdirs else ""
        libs = " ".join("-l" + l for l in dep.libs)
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_sdl2_ttf {inc} -L{libdir} {libs}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only compile+link verified")
            return
        self.run("./test_sdl2_ttf", env="conanrun")
