#!/usr/bin/env python3
"""Conan recipe for black (Python code formatter).

Build system: pip (hatchling backend)
Black is a pure Python package that uses hatch-vcs for version management.
The GitHub tarball lacks git metadata, so _black_version.py must be created
via patch and SETUPTOOLS_SCM_PRETEND_VERSION must be set.
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BlackConan(ConanFile):
    name = "black"
    version = "26.5.1"
    description = "The uncompromising Python code formatter"
    license = "MIT"
    homepage = "https://black.readthedocs.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"  # Recipe repo

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
        )
        apply_conandata_patches(self)

    def build(self):
        # Install to staging directory using pip
        site_packages = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        # Set environment for hatch-vcs version detection
        os.environ["SETUPTOOLS_SCM_PRETEND_VERSION"] = "26.5.1"
        if "TMPDIR" not in os.environ:
            os.environ["TMPDIR"] = "/tmp"
        self.run(
            f'pip3 install . --no-deps --no-build-isolation '
            f'--target="{site_packages}"',
            cwd=self.source_folder,
        )

    def package(self):
        # Move bin scripts from site-packages to bin/
        site_packages = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        src_bin = os.path.join(site_packages, "bin")
        dst_bin = os.path.join(self.package_folder, "bin")
        if os.path.isdir(src_bin):
            os.makedirs(dst_bin, exist_ok=True)
            for script in os.listdir(src_bin):
                shutil.move(os.path.join(src_bin, script), os.path.join(dst_bin, script))
            os.rmdir(src_bin)

        # Fix shebang to use python3
        for script_name in ("black", "blackd"):
            script_path = os.path.join(dst_bin, script_name)
            if os.path.isfile(script_path):
                with open(script_path, "r") as f:
                    content = f.read()
                content = content.replace(
                    "#!/data/service/hnp/bin/python3",
                    "#!/usr/bin/env python3",
                )
                with open(script_path, "w") as f:
                    f.write(content)
                st = os.stat(script_path)
                os.chmod(script_path, st.st_mode | stat.S_IEXEC)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib/python3.12/site-packages"]
        self.cpp_info.resdirs = ["lib/python3.12/site-packages"]
