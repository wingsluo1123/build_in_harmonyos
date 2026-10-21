import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps


class SofiaSipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build/generators"

    def generate(self):
        PkgConfigDeps(self).generate()
        AutotoolsToolchain(self).generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        compiler_map = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compiler_map.get("c", "clang")
        command = (
            "make -f {makefile} SOURCE_DIR={source} BUILD_DIR={build} CC={cc}"
        ).format(
            makefile=shlex.quote(os.path.join(self.source_folder, "Makefile")),
            source=shlex.quote(self.source_folder),
            build=shlex.quote(self.build_folder),
            cc=shlex.quote(cc),
        )
        self.run(command, cwd=self.build_folder, env="conanbuild")

    def test(self):
        if can_run(self):
            for name in ("test_sofia_consumer", "test_sofia_harmonyos"):
                executable = os.path.join(self.build_folder, name)
                self.run(shlex.quote(executable), cwd=self.build_folder, env="conanrun")
