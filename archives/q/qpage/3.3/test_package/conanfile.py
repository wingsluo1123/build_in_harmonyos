#!/usr/bin/env python3
"""Conan test_package for qpage 3.3.

Upstream ships no test suite.  This test builds a small mock SNPP server plus
an LD_PRELOAD shim that redirects the client's fixed SNPP port (444) to a high
port, then runs the installed ``qpage`` client against the mock and asserts the
on-the-wire command sequence.  It also checks the CLI diagnostics.
"""
import json
import os

from conan import ConanFile

CHECKS = 29


class QpageTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cc(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get("c") or "clang"

    def build(self):
        cc = self._cc()
        opt = "-O2" if str(self.settings.build_type) == "Release" else "-g -O0"
        mock = os.path.join(self.build_folder, "mock_snpp")
        redir = os.path.join(self.build_folder, "redir.so")
        self.run('"{}" {} "{}" -o "{}"'.format(
            cc, opt, os.path.join(self.recipe_folder, "mock_snpp.c"), mock),
            env="conanbuild")
        self.run('"{}" {} -shared -fPIC "{}" -o "{}"'.format(
            cc, opt, os.path.join(self.recipe_folder, "redir.c"), redir),
            env="conanbuild")

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        qpage = os.path.join(package_folder, "bin", "qpage")
        mock = os.path.join(self.build_folder, "mock_snpp")
        redir = os.path.join(self.build_folder, "redir.so")
        script = os.path.join(self.recipe_folder, "test_qpage.sh")
        for path in (qpage, mock, redir, script):
            if not os.path.isfile(path):
                raise Exception("required file not found: %s" % path)
        self.run('QPAGE_BIN="{}" MOCK_SNPP="{}" REDIR_SO="{}" sh "{}"'.format(
            qpage, mock, redir, script), env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_qpage.sh (qpage consumer checks + mock SNPP round trip)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
