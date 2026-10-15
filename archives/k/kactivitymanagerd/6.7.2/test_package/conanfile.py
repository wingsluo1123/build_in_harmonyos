#!/usr/bin/env python3
"""Conan test_package for kactivitymanagerd 6.7.2.

kactivitymanagerd is a D-Bus daemon application (no upstream test suite and
no exported CMake package config). The smoke test runs the packaged
kactivitymanagerd binary (R34: real artifact usage):

  - exit 0   -> daemon started, could not register the D-Bus service on the
                headless worker (no session bus) and exited cleanly
  - exit 124 -> daemon is up and serving (killed by the timeout guard)

Both outcomes prove the binary loads its Qt/KF6 dependencies and plugins
successfully on the target platform.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class KactivitymanagerdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        daemon = os.path.join(
            self.dependencies.get("kactivitymanagerd").cpp_info.bindirs[0],
            "kactivitymanagerd",
        )
        assert os.path.isfile(daemon), f"daemon binary missing: {daemon}"

        # Build the runtime env from the aggregated conanrun.sh: it carries
        # LD_LIBRARY_PATH for ALL dependencies, including transitive ones.
        # Manually iterating self.dependencies.values() only covers DIRECT
        # deps -- CI run #90750 failed with exit 127 because
        # libKF6CoreAddons.so (a transitive dep, pulled in by kcrash) was
        # missing from the hand-built LD_LIBRARY_PATH.
        # /system/lib64 is appended for OHOS: the sandbox LD_LIBRARY_PATH
        # contains an incompatible libc++_shared.so (kconfig 6.26.0
        # precedent).
        extra = ":/system/lib64" if self.settings.os == "OHOS" else ""
        script = os.path.join(os.path.dirname(__file__), "smoke_test.sh")
        cmd = ('. ./conanrun.sh && QT_QPA_PLATFORM=offscreen '
               'LD_LIBRARY_PATH="$LD_LIBRARY_PATH{}" '.format(extra))
        # smoke_test.sh wraps the daemon with a timeout guard: a live daemon
        # never exits on its own.
        ret = self.run(f'{cmd} "{script}" "{daemon}"', ignore_errors=True)
        if ret not in (0, 124):
            raise ConanException(
                f"kactivitymanagerd smoke test failed with exit code {ret}"
            )
