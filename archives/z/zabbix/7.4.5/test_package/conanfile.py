#!/usr/bin/env python3
"""Conan test_package for zabbix - verifies binaries are functional."""

from conan import ConanFile
from conan.tools.build import can_run


class ZabbixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            self.run("zabbix_agentd --version", env="conanrun")
            self.run("zabbix_get --version", env="conanrun")
            self.run("zabbix_sender --version", env="conanrun")
