import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")
        source = os.path.join(self.source_folder, "test_smpp34.c")
        if not os.path.isfile(source):
            source = os.path.join(self.recipe_folder, "test_smpp34.c")
        executable = os.path.join(self.build_folder, "test_smpp34")
        command = [
            f'"{cc}"',
            "-O1",
            f'-I"{os.path.join(dep.package_folder, "include")}"',
            f'"{source}"',
            "-o",
            f'"{executable}"',
            f'-L"{os.path.join(dep.package_folder, "lib")}"',
            "-lsmpp34",
            "-lpthread",
            "-lrt",
        ]
        self.run(" ".join(command))
        runtime = os.path.join(dep.package_folder, "lib")
        self.run(f'LD_LIBRARY_PATH="{runtime}" "{executable}"')
