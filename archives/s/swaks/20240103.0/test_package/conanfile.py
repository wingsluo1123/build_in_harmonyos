#!/usr/bin/env python3
"""Consumer test for swaks 20240103.0.

The packaged CLI is driven against a loopback SMTP sink
(test_package/mock_smtp.pl) and the test asserts on both swaks' own output and
the SMTP transcript the sink recorded.  The sink is started with the `perl`
that the recipe declares as a runtime requirement, so the dependency wiring
(perl reachable from the consumer's conanrun PATH) is part of what is tested
instead of being assumed.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class SwaksTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("cross build: swaks is a Perl script and was not executed")
            return

        tested = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(tested.package_folder, tested.cpp_info.bindirs[0])
        script = os.path.join(self.source_folder, "test_swaks.sh")
        # OHOS: run the driver with the shell the platform guarantees; the
        # script itself is POSIX sh and does not depend on bash extensions.
        shell = "/system/bin/sh" if str(self.settings.os) == "OHOS" else "sh"
        self.run(
            f'PATH="{bindir}:$PATH" "{shell}" "{script}" "{bindir}/swaks" "{self.build_folder}"',
            env="conanrun",
        )
