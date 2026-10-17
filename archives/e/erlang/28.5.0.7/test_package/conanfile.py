#!/usr/bin/env python3
"""Consumer test for the installed Erlang/OTP 28 command line tools.

test.sh drives the packaged erl/erlc/escript; the OHOS shell cannot execute ELF
binaries directly, so it is launched through bash.
"""
import os

from conan import ConanFile


class ErlangTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("%s test.sh" % bash, env="conanrun")
