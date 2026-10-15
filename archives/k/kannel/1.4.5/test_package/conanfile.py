import os
import io
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class KannelTest(ConanFile):
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

    def test(self):
        if can_run(self):
            self.run('"{}"'.format(os.path.join(self.cpp.build.bindirs[0], "consumer")), env="conanrun")
            package = self.dependencies["kannel"].package_folder
            config = os.path.join(package, "bin", "gw-config")
            output = io.StringIO()
            self.run(shlex.join([config, "--version"]), stdout=output)
            if output.getvalue().strip() != "1.4.5":
                raise RuntimeError("Installed gw-config version drift")
            flags = io.StringIO()
            self.run(shlex.join([config, "--cflags", "--libs"]), stdout=flags,
                     env="conanbuild")
            compiler = self.conf.get("tools.build:compiler_executables", check_type=dict)["c"]
            executable = os.path.join(self.build_folder, "config-consumer")
            self.run(shlex.join([compiler, os.path.join(self.source_folder, "test.c"),
                                 "-o", executable] + shlex.split(flags.getvalue())),
                     env="conanbuild")
            self.run(shlex.quote(executable), env="conanrun")
            self.output.info("KANNEL_CLI_RESULT=1/1 PASS")
