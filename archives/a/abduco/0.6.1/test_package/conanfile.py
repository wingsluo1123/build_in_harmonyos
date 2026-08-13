#!/usr/bin/env python3
import os
from conan import ConanFile


class AbducoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def test(self):
        abduco = self.dependencies["abduco"]
        # abduco 安装到 usr/bin（make install PREFIX=/usr）
        ab_bin = os.path.join(abduco.package_folder, "usr", "bin", "abduco")
        src = os.path.join(self.source_folder, "src", "test_abduco.c")
        test_bin = os.path.join(self.build_folder, "test_abduco")
        self.run(
            f"${{CC:-clang}} ${{CFLAGS}} -o \"{test_bin}\" \"{src}\"",
            env="conanbuild",
        )
        self.run(f'"{test_bin}" "{ab_bin}"', env="conanrun")
