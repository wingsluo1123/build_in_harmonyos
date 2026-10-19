#!/usr/bin/env python3
"""Conan test_package — ayatana-indicator-printers 23.10.1 (L1 test).

The product is a D-Bus daemon (no public library API), so the L1 test runs the
installed daemon against private D-Bus buses and observes its observable
behaviour (R34) instead of calling a library API:

  1. the installed data artifacts are present (indicator descriptor and
     autostart .desktop entry);
  2. the daemon binary is an executable ELF;
  3. the daemon connects to a system bus (it aborts with g_error() when the
     CUPS notification interface cannot be reached), owns
     org.ayatana.indicator.printers on the session bus and exports its
     indicator menu models;
  4. the daemon survives a CUPS PrinterStateChanged signal emitted by a peer
     playing the org.cups.cupsd.Notifier role.

The private buses are started with the dbus-daemon from the dbus package
(build context) because the indicator owns a *session* bus name while its CUPS
notifier lives on the *system* bus.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class AyatanaIndicatorPrintersTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Same glib track as the daemon requires; used by the D-Bus check.
        self.requires("glib/2.84.0.1")

    def build_requirements(self):
        # Private D-Bus daemons for the integration check (dbus-daemon /
        # dbus-send). Kept in the build context so that its own glib track does
        # not collide with the host dependency graph.
        self.tool_requires("dbus/1.14.10.3")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("skipped (cannot run on this platform)")
            return
        # OHOS /system/bin/sh (mksh) cannot run the test script; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        os.environ["PRINTERS_PKG"] = self.dependencies[
            self.tested_reference_str
        ].package_folder
        os.environ["DBUS_PKG"] = self.dependencies.build["dbus"].package_folder
        # D-Bus check helper built by this test_package (see CMakeLists.txt).
        os.environ["DBUS_CHECK_BIN"] = os.path.join(self.build_folder, "ohos-dbus-check")
        self.run(
            f"{bash} {os.path.join(self.recipe_folder, 'test.sh')}",
            env="conanrun",
            cwd=self.recipe_folder,
        )
