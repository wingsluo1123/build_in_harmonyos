#!/usr/bin/env python3
"""Conan test_package for esmtp 1.2.

esmtp is an SMTP relay client, so the consumer test is protocol-level (R34):
test.sh starts a local ESMTP listener on a loopback non-privileged TCP port
and drives a complete EHLO -> MAIL FROM -> RCPT TO -> DATA -> QUIT session
through the installed binary, then asserts on the recorded transcript.
It also checks the informational --version/--help options (patch 0001).
"""
import os

from conan import ConanFile


class EsmtpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
