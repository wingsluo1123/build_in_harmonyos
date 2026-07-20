import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        include_flags = []
        library_flags = []
        libs = ["-lmapserver"]
        for _ref, dep in self.dependencies.items():
            include_flags += ["-I" + path for path in dep.cpp_info.includedirs]
            for libdir in dep.cpp_info.libdirs:
                library_flags.append("-L" + libdir)
            libs += ["-l" + lib for lib in dep.cpp_info.libs if lib != "mapserver"]
            libs += ["-l" + lib for lib in dep.cpp_info.system_libs]
        cc = os.environ.get("CC", "clang")
        command = "{} test_mapserver.c -o test_mapserver {} {} {}".format(
            cc,
            " ".join(include_flags),
            " ".join(library_flags),
            " ".join(libs),
        )
        self.run(command)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link validation completed")
            return
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{shell} -c './test_mapserver'", env="conanrun")
        self.run(f"{shell} -c 'mapserv -v'", env="conanrun")
