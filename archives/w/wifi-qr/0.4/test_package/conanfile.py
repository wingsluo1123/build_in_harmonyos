#!/usr/bin/env python3
"""Conan test_package for wifi-qr 0.4 — script tool, no CMake build needed.

R34: must really invoke the tested tool. We run `wifi-qr -v` (version
report) and `wifi-qr -h` (usage header) with the dependency-provided
runtime environment (VirtualRunEnv brings qrencode/zbarimg into PATH).
"""
from conan import ConanFile
from conan.tools.env import VirtualRunEnv

import os


class WifiQrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        env = VirtualRunEnv(self)
        env.environment().define("TERM", "xterm")  # tput needs a terminal type
        # CI workers resolve the wifi-qr shebang (`/usr/bin/env bash`) inside
        # the conanrun environment, whose PATH does not include the OS bash.
        # CONFIG_SHELL (host profile buildenv) points at the real bash.
        cfg_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        env.environment().prepend_path("PATH", os.path.dirname(cfg_shell))
        env.generate()

    def test(self):
        # assertions live in test.sh (L0c requires a test source file);
        # run it with the VirtualRunEnv environment
        self.run('sh test.sh', env="conanrun")
