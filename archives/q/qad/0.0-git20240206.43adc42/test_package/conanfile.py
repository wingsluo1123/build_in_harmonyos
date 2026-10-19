#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.build import can_run


class QadTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        comp = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = comp.get("c") or "clang"
        incs = []
        for dep in self.dependencies.values():
            incs += ["-I" + p for p in dep.cpp_info.includedirs]
        self.run(f'{cc} -o consumer {os.path.join(self.recipe_folder, "consumer.c")} {" ".join(incs)}', env="conanbuild")

    def test(self):
        if can_run(self):
            self.run("./consumer", env="conanrun")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" test.sh', env="conanrun")
