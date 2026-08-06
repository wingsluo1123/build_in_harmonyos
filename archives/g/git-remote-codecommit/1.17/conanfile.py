#!/usr/bin/env python3
"""Conan recipe for git-remote-codecommit 1.17 — pure Python git remote helper for AWS CodeCommit.

This is a pure Python package (no C/C++ compilation). The recipe installs the
Python module and its runtime dependency botocore via pip, then creates a
console script wrapper that sets PYTHONPATH to find the bundled packages.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class GitRemoteCodecommitConan(ConanFile):
    name = "git-remote-codecommit"
    version = "1.17"
    description = "Git remote helper for AWS CodeCommit — simplifies pushing to and pulling from CodeCommit repositories"
    license = "Apache-2.0"
    homepage = "https://github.com/aws/git-remote-codecommit"
    url = ""

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        site_packages = os.path.join(self.build_folder, "site-packages")
        os.makedirs(site_packages, exist_ok=True)

        # Install the package and its dependency botocore via pip.
        # pip install <source_folder> resolves setup.py install_requires
        # (botocore >= 1.17.0) and downloads botocore + transitive deps
        # (jmespath, python-dateutil, urllib3, six) from PyPI.
        self.run(
            f'python3 -m pip install "{self.source_folder}" --target="{site_packages}" '
            f'--no-input'
        )

    def package(self):
        # Copy installed Python packages (module + botocore + deps)
        site_packages_src = os.path.join(self.build_folder, "site-packages")
        site_packages_dst = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        os.makedirs(site_packages_dst, exist_ok=True)
        copy(self, "*", src=site_packages_src, dst=site_packages_dst)

        # Copy license
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

        # Create console script wrapper that sets PYTHONPATH
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper = os.path.join(bin_dir, "git-remote-codecommit")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/usr/bin/env python3\n")
            f.write("import sys\n")
            f.write("import os\n")
            f.write("script_dir = os.path.dirname(os.path.abspath(__file__))\n")
            f.write("site_packages = os.path.join(script_dir, '..', 'lib', 'python3.12', 'site-packages')\n")
            f.write("sys.path.insert(0, site_packages)\n")
            f.write("from git_remote_codecommit import main\n")
            f.write("main()\n")
        os.chmod(wrapper, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["lib/python3.12/site-packages"]
