#!/usr/bin/env python3
"""Conan recipe for pipx 1.8.0 — pure Python package (pip install).

pipx is a Python CLI tool that installs and runs Python applications
in isolated environments. This recipe uses pip install to build
and package the tool for OHOS platform.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PipxConan(ConanFile):
    name = "pipx"
    version = "1.8.0"
    description = "Install and Run Python Applications in Isolated Environments"
    license = "MIT"
    homepage = "https://pipx.pipa.io"
    url = "https://github.com/pypa/pipx"

    settings = "os", "arch"

    python_version = "3.12"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No build system generators needed for pip install
        pass

    def build(self):
        # Apply patches if any
        apply_conandata_patches(self)

        site_packages = os.path.join(self.build_folder, "site-packages")
        bin_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(site_packages, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)

        # Set environment for pip in OHOS
        os.environ["SSL_CERT_FILE"] = "/storage/Users/currentUser/.opendesk/interpreters/pip-global/certifi/cacert.pem"
        os.environ.setdefault("PIP_INDEX_URL", "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple")
        os.environ.setdefault("PIP_TRUSTED_HOST", "pypi.cnb.cool")

        # Install pipx itself (no deps, we install them separately)
        self.run(
            f'python3 -m pip install . --no-deps --target="{site_packages}"',
            env="conanbuild",
        )

        # Install runtime dependencies
        deps = ["argcomplete>=1.9.4", "packaging>=20", "platformdirs>=2.1", "userpath>=1.6"]
        for dep in deps:
            self.run(
                f'python3 -m pip install "{dep}" --no-deps --target="{site_packages}"',
                env="conanbuild",
            )

        # Create the pipx executable wrapper script
        wrapper = os.path.join(bin_dir, "pipx")
        pyver = self.python_version
        with open(wrapper, "w") as f:
            f.write(
                "#!/system/bin/sh\n"
                f'PYTHONPATH="$PYTHONPATH:$(dirname $(dirname $0))/lib/python{pyver}/site-packages" '
                f'python3 -m pipx "$@"\n'
            )
        os.chmod(wrapper, 0o755)

    def package(self):
        # Copy site-packages to lib/python3.12/site-packages
        site_packages_src = os.path.join(self.build_folder, "site-packages")
        pyver = self.python_version
        target_site = os.path.join("lib", f"python{pyver}", "site-packages")
        copy(self, "*", site_packages_src, os.path.join(self.package_folder, target_site))

        # Copy the pipx wrapper script to bin/
        bin_src = os.path.join(self.build_folder, "bin")
        copy(self, "pipx", bin_src, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        pyver = self.python_version
        # cpp_info for Conan 2.x
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = [os.path.join("lib", f"python{pyver}", "site-packages")]
        # Also set env_info for backward compatibility
        bin_path = os.path.join(self.package_folder, "bin")
        site_path = os.path.join(self.package_folder, "lib", f"python{pyver}", "site-packages")
        self.env_info.PATH.append(bin_path)
        self.env_info.PYTHONPATH.append(site_path)
