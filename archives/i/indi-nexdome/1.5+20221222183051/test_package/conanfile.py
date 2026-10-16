#!/usr/bin/env python3
"""test_package for indi-nexdome — exercises the installed indi_nexdome driver.

R34: the tests really execute the packaged artifact.  indi_nexdome is an INDI
device server, so the consumer tests drive it through the INDI XML protocol on
stdin/stdout (exactly like indiserver does) plus the framework CLI handling.
"""
import os
import shutil

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(pkg, "bin", "indi_nexdome")
        if not os.path.isfile(binary):
            raise FileNotFoundError(f"packaged driver not found: {binary}")

        # /system/bin/sh (mksh) cannot exec ELF binaries on this platform; use
        # bash (same wrapper as the other OHOS recipes in this repository).
        bash = os.environ.get("CONFIG_SHELL", "")
        if not (bash and os.path.isfile(bash)):
            bash = shutil.which("bash") or ""
        if not (bash and os.path.isfile(bash)):
            fallback = "/data/service/hnp/bin/bash"
            bash = fallback if os.path.isfile(fallback) else ""
        if not bash:
            raise FileNotFoundError("bash not found (set CONFIG_SHELL or add bash to PATH)")

        self.run(f'"{bash}" test.sh "{binary}"',
                 env="conanrun", cwd=self.source_folder)
        self.run(f'"{bash}" test_ohos.sh "{pkg}"',
                 env="conanrun", cwd=self.source_folder)
