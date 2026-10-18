#!/usr/bin/env python3
"""test_package for sircbot — consumer end-to-end test of the installed binaries.

``consumer_test.sh`` starts a minimal IRC server as the peer, launches the
installed ``sircbot`` daemon against it, pushes a message through the installed
``sircbot-send``, and verifies that the message reached the IRC server and that
an inbound message ran the channel hook with the documented arguments.
"""
import os

from conan import ConanFile


class SircbotTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} consumer_test.sh", env="conanrun")
