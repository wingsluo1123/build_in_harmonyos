#!/usr/bin/env python3
"""L1 test for runuser: verify the runuser binary was built and runs."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class RunuserTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        if can_run(self):
            pkg = self.dependencies["runuser"]
            bindir = pkg.cpp_info.bindirs[0]
            runuser_bin = os.path.join(bindir, "runuser")
            # Use the compiler from the toolchain configuration (R33: no
            # hard-coded compiler names in build scripts).
            cc = "clang"
            execs = self.conf.get("tools.build:compiler_executables", default={})
            if isinstance(execs, dict) and execs.get("c"):
                cc = execs["c"]
            self.run(
                f"{cc} test.c -o test_runuser",
                env="conanbuild",
            )
            # Store path for test()
            self._runuser_bin = runuser_bin

    def test(self):
        if can_run(self):
            pkg = self.dependencies["runuser"]
            bindir = pkg.cpp_info.bindirs[0]
            runuser_bin = os.path.join(bindir, "runuser")
            # Run the compiled C test (uses execv to call runuser --version/--help)
            self.run(
                f"./test_runuser {runuser_bin}",
                env="conanrun",
            )
            # Also try running runuser --version directly for additional verification
            self.run(f"{runuser_bin} --version", env="conanrun", ignore_errors=True)
            self.output.info("OK: runuser smoke test completed")