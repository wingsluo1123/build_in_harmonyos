#!/usr/bin/env python3
"""Conan test_package for sinfo 0.0.48 — consumer verification.

Runs the real installed `sinfo` (client) and `sinfod` (daemon) through
test_sinfo.sh: version/help assertions for both binaries, then a real
end-to-end exchange — sinfod is started in foreground with its broadcast
address narrowed to loopback (-b 127.0.0.1), the sinfo client queries it
over UDP and TCP (SINFO_REQUEST_PORT 60002) in hostsmode (-H) and
loadmode (-L), and the daemon exits cleanly on SIGTERM.

The interactive ncurses UI is not exercised (needs a real terminal);
-H/-L print plain text to stdout without initialising curses.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class SinfoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "build"

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["sinfo"]
        # package_info.bindirs = ["bin"]（Conan 工具链默认 --sbindir 重定向，
        # sinfo 客户端与 sinfod 守护同落 bin/）
        sinfo_bin = os.path.join(dep.cpp_info.bindirs[0], "sinfo")
        sinfod_bin = os.path.join(dep.cpp_info.bindirs[0], "sinfod")
        script = os.path.join(self.source_folder, "test_sinfo.sh")
        self.run(f'sh "{script}" "{sinfo_bin}" "{sinfod_bin}"', env="conanrun")
