#!/usr/bin/env python3
"""Conan recipe for talloc 2.4.2 (waf build system from Samba).

talloc uses a waf-based build system wrapped in a configure/make interface.
Key OHOS adaptations:
  - --disable-python: Python embedding doesn't work on OHOS
  - Patch: HAVE_SECURE_MKSTEMP check uses /tmp (read-only on OHOS), made non-mandatory
"""
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsLayout


class TallocConan(ConanFile):
    name = "talloc"
    version = "2.4.2"
    description = "Talloc is a hierarchical, reference counted memory pool system with destructors"
    license = "MIT"
    homepage = "https://talloc.samba.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        AutotoolsLayout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # talloc uses waf, not autotools - filter out args waf doesn't understand
        # Keep --prefix, remove --enable-shared, --disable-shared, --enable-static,
        # --disable-static, and any args containing ${} (waf can't expand them)
        tc.configure_args = [
            arg for arg in tc.configure_args
            if not arg.startswith("--enable-shared")
            and not arg.startswith("--disable-shared")
            and not arg.startswith("--enable-static")
            and not arg.startswith("--disable-static")
            and "${" not in arg
        ]
        tc.configure_args.append("--disable-python")
        # Set PYTHON env var for waf (configure wrapper calls $PYTHON)
        # Use shutil.which for robust path detection (R33: avoid hardcoded paths)
        python_path = shutil.which("python3") or "/data/service/hnp/bin/python3"
        env = tc.environment()
        env.define("PYTHON", python_path)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["talloc"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
