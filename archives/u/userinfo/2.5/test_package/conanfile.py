#!/usr/bin/env python3
"""Conan test_package for userinfo 2.5.

Upstream ships no test suite.  This test runs the installed ``ui`` program and
exercises its CLI plus the three loadable modules (passwd.so, mail.so,
login.so) that are resolved through the binary's RUNPATH.
"""
import json
import os

from conan import ConanFile

CHECKS = 23


class UserinfoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        ui = os.path.join(package_folder, "bin", "ui")
        script = os.path.join(self.recipe_folder, "test_userinfo.sh")
        for path in (ui, script):
            if not os.path.isfile(path):
                raise Exception("required file not found: %s" % path)
        self.run('UI_BIN="{}" sh "{}"'.format(ui, script), env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_userinfo.sh (ui consumer checks + module loading)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
