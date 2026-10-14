import os
import platform

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class TmAlignTestConan(ConanFile):
    """Consumer test: build a C++ driver that generates PDB structures and checks the packaged TMalign / TMscore."""

    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = os.path.join(self.dependencies[self.tested_reference_str].package_folder, "bin")
        tmalign = os.path.join(bindir, "TMalign")
        tmscore = os.path.join(bindir, "TMscore")
        driver = os.path.join(self.cpp.build.bindirs[0], "test_tmalign")
        for path in (tmalign, tmscore, driver):
            if not os.path.isfile(path):
                raise ConanException(f"expected file not found: {path}")
        # aarch64 ELF binaries only execute on an aarch64 host (an x86 runner
        # has no /lib/ld-musl-aarch64.so.1); otherwise only the build is checked.
        if cross_building(self) or platform.machine().lower() not in ("aarch64", "arm64"):
            self.output.warning("non-aarch64 host: consumer binary built and linked, runtime test skipped")
            return
        self.run(f'"{driver}" "{tmalign}" "{tmscore}"', env="conanrun", cwd=self.build_folder)
