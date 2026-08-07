import os
from conan import ConanFile


class TestPdf4QtConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify pdf4qt library exists and is a valid shared library
        pdf4qt = self.dependencies["pdf4qt"]
        lib_dir = pdf4qt.cpp_info.libdirs[0] if pdf4qt.cpp_info.libdirs else ""
        lib_path = os.path.join(lib_dir, "libPdf4QtLibCore.so")

        if not os.path.exists(lib_path):
            raise Exception(f"Library not found: {lib_path}")

        # Verify it's a valid ELF shared library for aarch64
        self.run(f"file {lib_path}")
        self.run(f"readelf -h {lib_path}")
