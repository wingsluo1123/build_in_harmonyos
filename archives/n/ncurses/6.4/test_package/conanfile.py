import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["ncurses"].cpp_info
        inc = " ".join("-I" + d for d in dep.includedirs)
        pkg_folder = str(getattr(self.dependencies["ncurses"], "package_folder", "") or "")
        lib_paths = []
        for libdir in dep.libdirs:
            lib_paths.append(f"-L{os.path.join(pkg_folder, str(libdir))}")
        libs = " ".join("-l" + l for l in dep.libs)
        libdir_str = " ".join(lib_paths)
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_ncurses {inc} {libdir_str} {libs}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only compile+link verified")
            return
        # ncurses tests need a terminal, skip runtime test
        self.output.info("ncurses: compile+link verified (terminal not available)")
