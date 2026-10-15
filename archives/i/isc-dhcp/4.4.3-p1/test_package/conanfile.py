#!/usr/bin/env python3
"""Conan test_package — isc-dhcp 4.4.3-p1 (consumer view).

Builds and runs a real consumer of the packaged artefacts: a C program that
links the packaged libraries (libomapi/libdhcpctl/libdhcp plus the bundled
BIND closure) and exercises the public OMAPI API — omapi_init(), the
dhcpctl control-channel entry points and the connection path.  The packaged
programs are then run directly (dhcpd/dhclient/dhcrelay --version), which
proves the executables load and run on the target.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class IscDhcpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: consumer test skipped")
            return
        bindir = self.cpp.build.bindirs[0]
        pkg = self.dependencies[self.tested_reference_str].package_folder

        # 1) The packaged programs: the three DHCP daemons print their
        #    version and exit 0 — the executables load and run on the target
        #    (serving real traffic needs live sockets/interfaces, which the
        #    test environment cannot provide).
        for exe in ("dhcpd", "dhclient", "dhcrelay"):
            self.run('"{}/bin/{}" --version'.format(pkg, exe), env="conanrun")

        # 2) omshell has no --version flag (running it with one prints its
        #    usage and exits 1): feed it an empty command list instead — it
        #    reads the prompts to EOF and exits 0, which proves the binary
        #    loads and runs on the target.
        omshell_cmd = 'echo | "{}/bin/omshell"'.format(pkg)
        self.run(omshell_cmd, env="conanrun")

        # 3) API consumer of the packaged libraries.
        self.run('"{}/test_package"'.format(bindir), env="conanrun")
