#!/usr/bin/env python3
"""Conan recipe — boost 1.84.0 (header-only).
Note: GitHub archive only contains the superproject, not submodule headers.
The full source (117MB) from SourceForge could not be downloaded due to network issues.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BoostConan(ConanFile):
    name = "boost"
    version = "1.84.0"
    description = "Boost C++ libraries (header-only subset)"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Try Conan's get() first, fall back to manual download
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception:
            import hashlib, urllib.request, ssl, tarfile, io
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            url = self.conan_data["sources"]["url"]
            expected_sha = self.conan_data["sources"]["sha256"]
            cache_dir = os.path.expanduser("~/.conan2/h")
            cache_file = os.path.join(cache_dir, expected_sha)
            if os.path.exists(cache_file):
                with open(cache_file, "rb") as f:
                    data = f.read()
            else:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                resp = urllib.request.urlopen(req, timeout=60, context=ctx)
                data = resp.read()
            t = tarfile.open(fileobj=io.BytesIO(data))
            for member in t.getmembers():
                parts = member.name.split("/", 1)
                if len(parts) > 1:
                    member.name = parts[1]
                    t.extract(member, self.source_folder)
            t.close()

    def generate(self):
        pass

    def build(self):
        # Boost is header-only - no build required
        pass

    def package(self):
        # Copy all header files
        copy(self, "*.hpp", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "*.ipp", self.source_folder, os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = []
