import os

from conan import ConanFile
from conan.tools.build import can_run


class VomsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["voms"].package_folder
        openssl = self.dependencies["openssl"].package_folder
        expat = self.dependencies["expat"].package_folder
        cxx = os.environ.get("CXX", "clang++")
        src = os.path.join(self.source_folder, "test_voms.cpp")
        # voms 公共头依赖 openssl 头，且链接需 openssl/expat 库路径
        self.run(
            f"{cxx} -std=c++17 -o test_voms {src} "
            f"-I{pkg}/include -I{openssl}/include "
            f"-L{pkg}/lib -L{openssl}/lib -L{expat}/lib "
            f"-lvomsapi -lssl -lcrypto -lexpat",
            env="conanbuild",
        )

    def test(self):
        if can_run(self):
            libdirs = ":".join(
                os.path.join(self.dependencies[n].package_folder, "lib")
                for n in ("voms", "openssl", "expat")
            )
            bin_path = os.path.join(self.build_folder, "test_voms")
            self.run(f"LD_LIBRARY_PATH='{libdirs}' {bin_path}", env="conanrun")
