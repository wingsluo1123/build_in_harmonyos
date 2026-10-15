#!/usr/bin/env python3
"""test_package — scrollz 2.2.3 consumer smoke test.

The produced artifact is the `scrollz` executable (CLI tool, not a library).
test() executes the L0c test source `smoke_test.sh` via self.run, which really
runs the packaged binary and asserts observable output:

  1. `scrollz --version` — option parsing skips the leading dashes and hits the
     `v` switch, calling show_version(), which prints the ircII/ScrollZ version
     banner and exits 0 (a real CLI path, no interactive terminal needed).
  2. `scrollz -v` — the upstream single-dash version switch, same banner.

The ncurses dependency is declared so its runenv is aggregated into the
conanrun environment (env="conanrun").
"""
import os

from conan import ConanFile


class ScrollzTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("ncurses/6.5")

    def test(self):
        dep = self.dependencies["scrollz"]
        exe = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "scrollz")
        script = os.path.join(self.source_folder, "smoke_test.sh")
        self.run(f'sh "{script}" "{exe}"', env="conanrun")
