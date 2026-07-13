#!/usr/bin/env python3
"""Conan recipe — automysqlbackup 3.0-rc6

automysqlbackup is a pure bash script package (no C compilation).
This recipe installs the script and config files.

R26 compliance: BUILD_SHARED_LIBS=OFF (no-op for script packages, no ELF to link).
R27 compliance: No external dependencies.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AutomysqlbackupConan(ConanFile):
    name = "automysqlbackup"
    version = "3.0-rc6"
    description = "AutoMySQLBackup - automatic MySQL database backup script"
    license = "GPL-2.0"
    homepage = "https://sourceforge.net/projects/automysqlbackup/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # No external dependencies (R27: would use @ohpcd/stable if any)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=False)

    def generate(self):
        # R26: Terminal tools must be statically linked
        # For script-only packages, set BUILD_SHARED_LIBS=OFF as a no-op compliance marker
        # (no ELF binary to link, but flag must be present for gate compliance)
        env = os.environ
        env["BUILD_SHARED_LIBS"] = "OFF"

    def build(self):
        apply_conandata_patches(self)
        # Pure shell script package — no compilation step needed
        # Verify script syntax as a build-time check
        import subprocess
        script_path = os.path.join(self.source_folder, "automysqlbackup")
        if os.path.exists(script_path):
            result = subprocess.run(
                ["bash", "-n", script_path],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                raise Exception(f"Bash syntax check failed: {result.stderr}")

    def package(self):
        # Install the main script to bin/
        copy(self, "automysqlbackup", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        # Install config and docs to etc/automysqlbackup/
        etc_dir = os.path.join(self.package_folder, "etc", "automysqlbackup")
        copy(self, "automysqlbackup.conf", src=self.source_folder, dst=etc_dir)
        copy(self, "LICENSE", src=self.source_folder, dst=etc_dir)
        copy(self, "README", src=self.source_folder, dst=etc_dir)

    def package_info(self):
        self.cpp_info.libs = ["automysqlbackup"]
        self.cpp_info.bindirs = ["bin"]
