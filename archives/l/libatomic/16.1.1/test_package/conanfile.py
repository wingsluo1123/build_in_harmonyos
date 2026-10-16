import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class LibatomicTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        executable = self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")
        library = os.path.join(self.dependencies["libatomic"].package_folder,
                               "lib", "libatomic.a")
        source = os.path.join(self.source_folder, "test.c")
        binary = os.path.join(self.build_folder, "test_libatomic")
        self.run(f'"{executable}" "{source}" "{library}" -o "{binary}"', env="conanbuild")

    def test(self):
        binary = os.path.join(self.build_folder, "test_libatomic")
        self.run(f'"{binary}"', env="conanrun")
