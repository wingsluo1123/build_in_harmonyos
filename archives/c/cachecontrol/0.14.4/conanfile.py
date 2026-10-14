#!/usr/bin/env python3
"""Conan recipe for cachecontrol 0.14.4 — httputil caching layer for requests.

Pure Python (cachecontrol/), build backend uv_build (irrelevant here —
copytree staging per awscli WR-008). Runtime deps per PyPI requires_dist:
  - requests>=2.16.0        -> requests/2.22.0 (ohpcd published)
  - msgpack<2.0.0,>=0.5.2   -> python-msgpack/1.1.1 (NEW: ohpcd's
                               msgpack/7.0.1 is msgpack-c, the C library,
                               and does NOT provide the Python module)
  - [filecache] extra: filelock>=3.8.0 -> filelock/3.32.7 (NEW; required
                               by lastversion's `from cachecontrol.caches.
                               file_cache import FileCache` startup path,
                               i.e. cachecontrol[filecache] semantics)
redis (extra) is TYPE_CHECKING-only — no runtime dep. No source patch
required on OHOS.

R38 note: no console_scripts entry point (the `doesitcache` CLI module is
not declared upstream), no bin/ payload — library only.
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get)


class CachecontrolConan(ConanFile):
    name = "cachecontrol"
    version = "0.14.4"
    package_type = "python-require"
    license = "Apache-2.0"
    homepage = "https://github.com/psf/cachecontrol"
    description = ("httplib2 caching for requests (cachecontrol[filecache]; "
                   "lastversion dependency)")
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"

    requires = (
        "requests/2.22.0",
        "python-msgpack/1.1.1",
        "filelock/3.32.7",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"]["cachecontrol"],
            strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        staging = os.path.join(self.build_folder, "cachecontrol-stage")
        shutil.rmtree(staging, ignore_errors=True)
        src_pkg = os.path.join(self.source_folder, "cachecontrol")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"cachecontrol package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(staging, "cachecontrol"),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def package(self):
        staging = os.path.join(self.build_folder, "cachecontrol-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(
            os.path.join(staging, "cachecontrol"),
            os.path.join(site, "cachecontrol"),
            ignore=shutil.ignore_patterns("__pycache__"))

        # upstream __init__.py resolves __version__ via importlib.metadata
        # unguarded — the copytree port must ship a minimal dist-info
        # (equivalent of what pip install would leave behind)
        dist_info = os.path.join(site, "cachecontrol-0.14.4.dist-info")
        os.makedirs(dist_info, exist_ok=True)
        with open(os.path.join(dist_info, "METADATA"), "w", newline="\n") as f:
            f.write("Metadata-Version: 2.1\n"
                    "Name: cachecontrol\n"
                    "Version: 0.14.4\n"
                    "Summary: httplib2 caching for requests\n")
        with open(os.path.join(dist_info, "WHEEL"), "w", newline="\n") as f:
            f.write("Wheel-Version: 1.0\n"
                    "Generator: conan-copytree-port\n"
                    "Root-Is-Purelib: true\n"
                    "Tag: py3-none-any\n")

        src_lic = os.path.join(self.source_folder, "LICENSE.txt")
        if os.path.isfile(src_lic):
            lic_dir = os.path.join(self.package_folder, "licenses")
            os.makedirs(lic_dir, exist_ok=True)
            shutil.copy2(src_lic, os.path.join(lic_dir, "LICENSE.txt"))

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
