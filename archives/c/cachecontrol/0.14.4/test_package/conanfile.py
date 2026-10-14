#!/usr/bin/env python3
"""Conan test_package for cachecontrol 0.14.4 — consumer check (R34).

Assembles site-packages of the tested package plus the whole dependency
graph (requests chain incl. chardet/idna/urllib3/certifi, python-msgpack,
filelock) into one PYTHONPATH — awscli precedent, generalized to iterate
all graph nodes. All assertions run offline (fabricated urllib3 response,
temp FileCache directory).
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class CachecontrolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["cachecontrol"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        paths = []
        for dep in self.dependencies.values():
            sp = os.path.join(dep.package_folder, "lib", py_ver,
                              "site-packages")
            if os.path.isdir(sp):
                paths.append(sp)
        # de-duplicate, keep order (tested package first)
        paths = list(dict.fromkeys(paths))
        site_all = os.pathsep.join(paths)
        if not os.path.isfile(os.path.join(paths[0], "cachecontrol",
                                           "__init__.py")):
            raise ConanException(f"cachecontrol missing under {paths[0]}")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_cachecontrol.py")
        if not os.path.isfile(test_script):
            raise ConanException(
                f"test_cachecontrol.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site_all}'", env="conanrun")
