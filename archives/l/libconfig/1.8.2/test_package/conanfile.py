import os
from pathlib import Path
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from ohos_sign import sign_elf


class LibconfigTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if str(self.settings.os) == "OHOS":
            for name in ("consumer_c", "consumer_cpp"):
                sign_elf(Path(self.build_folder, "bin", name))

    def test(self):
        if can_run(self):
            scratch = Path(self.build_folder, "consumer-tmp")
            scratch.mkdir(mode=0o770, exist_ok=False)
            env = Environment()
            env.define("TMPDIR", str(scratch))
            with env.vars(self).apply():
                for name in ("consumer_c", "consumer_cpp"):
                    self.run('"{}"'.format(Path(self.build_folder, "bin", name)), env="conanrun")
            self.output.info("CONSUMER_1_OF_1_PASS")
