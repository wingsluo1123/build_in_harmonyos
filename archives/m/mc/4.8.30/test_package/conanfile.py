#!/usr/bin/env python3
"""Conan test_package for mc 4.8.30.

Verifies the mc binary is functional by running test_mc.sh.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class McTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # Find the mc binary path
        mc_bin = None

        # Try deps_cpp_info (Conan 1.x)
        try:
            mc_info = self.deps_cpp_info["mc"]
            for bindir in mc_info.bindirs:
                candidate = os.path.join(bindir, "mc")
                if os.path.isfile(candidate):
                    mc_bin = candidate
                    break
        except AttributeError:
            pass

        # Try dependencies (Conan 2.x)
        if not mc_bin:
            try:
                mc_info = self.dependencies["mc"].cpp_info
                for bindir in mc_info.bindirs:
                    candidate = os.path.join(bindir, "mc")
                    if os.path.isfile(candidate):
                        mc_bin = candidate
                        break
            except (AttributeError, KeyError):
                pass

        # Set MC_BIN env var for the test script
        if mc_bin:
            os.environ["MC_BIN"] = mc_bin

        # Run the test script
        test_script = os.path.join(os.path.dirname(__file__), "test_mc.sh")
        self.run(f'"{test_script}"', env="conanrun")
