#!/usr/bin/env python3
"""test_package for dnsfunnel — L1 consumer test.

The package ships two CLI tools and no library, so the consumer test runs the
real installed binaries (linked against skalibs/s6-dns) and asserts on their
observable behaviour:

  1. dnsfunneld rejects an unknown option with the upstream usage text (100)
  2. dnsfunnel-translate parses a resolv.conf and writes the cache list
  3. dnsfunnel-translate reports a missing input file with exit 111
  4. dnsfunneld binds an unprivileged loopback port and reports readiness
  5. dnsfunneld forwards a real DNS query end to end (answer comes back)

Everything runs through the conanrun environment (R34/L1e).
"""
import os
import shlex

from conan import ConanFile


class DnsfunnelTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # test.sh needs bash (set -euo pipefail); the profile buildenv puts
        # CONFIG_SHELL on every machine, fall back to "bash" from PATH.
        shell = os.environ.get("CONFIG_SHELL", "").strip() or "bash"
        self.run(f"{shlex.quote(shell)} {shlex.quote('test.sh')}", env="conanrun")
