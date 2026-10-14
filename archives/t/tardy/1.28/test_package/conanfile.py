#!/usr/bin/env python3
"""Consumer test for tardy/1.28 (tool package).

Runs the installed `tardy` binary through a shell contract test
(version, help, prefix roundtrip on a system-tar fixture).
"""
from conan import ConanFile
from conan.tools.env import Environment


class TardyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Neutralize ambient LD_LIBRARY_PATH (some CI workers point it at
        # a /usr/local/lib whose incompatible libxml2.so.16 breaks the
        # SDK's lld on every link — CI-021 build #48068, libabw precedent).
        environment = Environment()
        environment.define("LD_LIBRARY_PATH", "")
        with environment.vars(self).apply():
            # The verdict is taken by running the consumer script directly
            # under the package's runtime environment (env="conanrun"),
            # which puts the installed bin/ on PATH.
            self.run("sh test_tardy.sh", cwd=self.source_folder,
                     env="conanrun")
