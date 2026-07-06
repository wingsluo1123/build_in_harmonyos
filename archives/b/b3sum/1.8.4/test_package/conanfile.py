import os

from conan import ConanFile


class B3sumTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # b3sum package provides libblake3.a + blake3.h (no binary tool)
        dep = self.dependencies["b3sum"]
        cpp = dep.cpp_info
        inc = " ".join(f"-I{d}" for d in cpp.includedirs)
        lib = " ".join(f"-L{d}" for d in cpp.libdirs)
        cc = os.environ.get("CC", "clang")

        test_src = os.path.join(self.source_folder, "test.c")
        test_bin = os.path.join(self.build_folder, "test_b3sum")

        self.run(f"{cc} {test_src} -o {test_bin} {inc} {lib} -lblake3")
        self.run(f"{test_bin}", env="conanrun")
