import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        include_flags = []
        library_flags = []
        for _ref, dep in self.dependencies.items():
            include_flags += ["-I" + path for path in dep.cpp_info.includedirs]
            for libdir in dep.cpp_info.libdirs:
                library_flags.append("-L" + libdir)
        libs = ["-lgdal"]
        for _ref, dep in self.dependencies.items():
            libs += ["-l" + lib for lib in dep.cpp_info.libs if lib != "gdal"]
            libs += ["-l" + lib for lib in dep.cpp_info.system_libs]
        executables = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cxx = executables.get("cpp") or executables.get("cxx")
        if not cxx:
            raise ConanException("C++ compiler not found in tools.build:compiler_executables")
        test_source = os.path.join(self.source_folder, "test_gdal.cpp")
        test_binary = os.path.join(self.build_folder, "test_gdal")
        command = '{} "{}" -o "{}" {} {} {}'.format(
            cxx,
            test_source,
            test_binary,
            " ".join(include_flags),
            " ".join(library_flags),
            " ".join(libs),
        )
        self.run(command, env="conanbuild")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link validation completed")
            return
        self.run(os.path.join(self.build_folder, "test_gdal"), env="conanrun")
