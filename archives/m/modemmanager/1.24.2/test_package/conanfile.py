#!/usr/bin/env python3
"""Conan test_package — modemmanager 1.24.2 (libmm-glib) consumer test.

Compiles and runs a C program against the packaged libmm-glib: verifies the
installed headers (ModemManager.h + libmm-glib.h), the GType registrations
of the core client objects (MmModem/MmManager/MmObject/MmSim/MmBearer/
MmSms/MmCall), the shared enum values (MM_MODEM_STATE_REGISTERED), the
generated type registrations (mm_core_error_quark /
mm_modem_capability_get_type) and the version macros (1.24.2), without
requiring a running ModemManager daemon or D-Bus system bus.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ModemmanagerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # test source also uses glib directly (g_print / g_type_name / GQuark)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(self.cpp.build.bindirs[0], "test_modemmanager" + suffix)
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
