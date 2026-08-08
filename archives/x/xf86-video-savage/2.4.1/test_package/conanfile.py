#!/usr/bin/env python3
"""Conan test_package for xf86-video-savage 2.4.1.

Verifies the savage_drv.so X.Org driver module:
1. File exists in the package
2. Valid ELF shared object
3. Exports savageModuleData symbol (via dlopen test)
"""
import os
import shutil
from conan import ConanFile
from conan.tools.layout import basic_layout


class Xf86VideoSavageTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Compile the test program
        cc = str(self.settings.compiler) if hasattr(self, 'settings') and self.settings.compiler else "clang"
        cc_path = shutil.which(cc) or shutil.which("clang") or "/data/service/hnp/bin/clang"
        test_src = os.path.join(os.path.dirname(__file__), "test.c")
        test_bin = os.path.join(self.build_folder, "test_savage_drv")
        self.run(f'{cc_path} -fPIC -o "{test_bin}" "{test_src}" -ldl')
        self._test_bin = test_bin

    def test(self):
        # Find savage_drv.so in the package
        libdirs = self.dependencies["xf86-video-savage"].cpp_info.libdirs
        found = False
        so_path = None
        for libdir in libdirs:
            so_path = os.path.join(libdir, "savage_drv.so")
            if os.path.isfile(so_path):
                self.output.info(f"Found savage_drv.so at {so_path}")
                found = True
                # Check it's an ELF file
                with open(so_path, "rb") as f:
                    magic = f.read(4)
                    assert magic == b"\x7fELF", f"Not an ELF file: {magic}"
                    self.output.info("ELF magic check: PASS")
                break

        assert found, "savage_drv.so not found in package"

        # Run the test program
        test_bin = os.path.join(self.build_folder, "test_savage_drv")
        if os.path.isfile(test_bin):
            self.run(f'"{test_bin}" "{so_path}"')
        self.output.info("All tests passed: savage_drv.so verified")
