#!/usr/bin/env python3
"""Exercise installed IRAF tools and the packaged AArch64 context routines."""
import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.layout import basic_layout


class IrafTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["iraf"]
        compiler = self.conf.get("tools.build:compiler_executables", default={}).get("c", "cc")
        command = "TMPDIR=" + shlex.quote(self.build_folder) + " CC=" + shlex.quote(compiler)
        command += " IRAF_PACKAGE=" + shlex.quote(dep.package_folder)
        command += " IRAF_TEST_SOURCES=" + shlex.quote(self.source_folder)
        # The OHOS system sh writes here-documents under read-only /tmp.
        # zsh is the repository CI shell and honors the writable TMPDIR.
        command += " zsh " + shlex.quote(os.path.join(self.source_folder, "test_iraf.sh"))
        self.run(command, env=["conanbuild", "conanrun"])
