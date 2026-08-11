#!/usr/bin/env python3
"""Conan test_package — gpgmepy 2.0.0 (GPGME Python bindings) consumer test.

R34 real test: import the installed `gpg` module from the package and verify:
  1. gpg.version.versionstr == "2.0.0"      (binding version)
  2. gpg.version.gpgme_versionstr == "1.24.0" (proves the SWIG extension is
     linked against the conan-provided libgpgme)
  3. gpg.Data() can be constructed          (C API round-trip)
No GnuPG engine (gpg binary) is required for these checks.

PYTHONPATH is injected from the package's lib/python3.12/site-packages;
LD_LIBRARY_PATH for libgpgme/libgpg-error/libassuan comes from the transitive
dependencies' libdirs.
"""
import os
import sys

from conan import ConanFile


class GpgmepyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        pv = "python{}.{}".format(sys.version_info.major, sys.version_info.minor)
        site_packages = os.path.join(pkg, "lib", pv, "site-packages")
        smoke = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke.py")

        # LD_LIBRARY_PATH: libgpgme / libgpg-error / libassuan (transitive deps)
        ld_paths = []
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                if libdir:
                    ld_paths.append(os.path.join(dep.package_folder, libdir))

        old_py = os.environ.get("PYTHONPATH")
        old_ld = os.environ.get("LD_LIBRARY_PATH")
        os.environ["PYTHONPATH"] = site_packages + (os.pathsep + old_py if old_py else "")
        os.environ["LD_LIBRARY_PATH"] = ":".join(ld_paths) + (":" + old_ld if old_ld else "")
        try:
            ret = self.run("python3 {} 2>&1".format(smoke))
            if ret != 0:
                raise Exception("test_package smoke.py failed with exit code %s" % ret)
        finally:
            if old_py is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = old_py
            if old_ld is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = old_ld
