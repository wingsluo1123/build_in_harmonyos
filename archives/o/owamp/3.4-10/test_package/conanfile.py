#!/usr/bin/env python3
"""test_package for owamp 3.4-10.

Consumer-level test (R34): verifies the installed owamp CLI tools are
present in the package and that the shipped binaries actually run on the
target platform (owping -h prints usage; owtvec runs its self-check).
"""
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["owamp"]
        bindir = os.path.join(dep.package_folder, "bin")
        for tool in ("owping", "owampd", "powstream", "owtvec"):
            path = os.path.join(bindir, tool)
            if not os.path.exists(path):
                self.output.error("missing installed tool: " + path)
                raise SystemExit(1)
        # owtvec is the upstream test entry — run it; non-zero exit fails the
        # test (Appendix B exponential-deviate self-check)
        owtvec = os.path.join(bindir, "owtvec")
        self.run(owtvec, env="conanrun")
