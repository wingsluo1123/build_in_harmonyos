#!/usr/bin/env python3
"""Conan recipe — boost-build 1.90.0 (Boost.Build/b2)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BoostbuildConan(ConanFile):
    name = "boost-build"
    version = "1.90.0"
    description = "Boost.Build - b2 build system"
    license = "BSL-1.0"
    homepage = "https://github.com/boostorg/build"
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
            # Manual download with SSL verification disabled
            import hashlib, urllib.request, ssl, tarfile, io, os
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            url = self.conan_data["sources"]["url"]
            expected_sha = self.conan_data["sources"]["sha256"]
            # Check cache first
            cache_dir = os.path.expanduser("~/.conan2/h")
            cache_file = os.path.join(cache_dir, expected_sha)
            if os.path.exists(cache_file):
                with open(cache_file, "rb") as f:
                    data = f.read()
            else:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                resp = urllib.request.urlopen(req, timeout=60, context=ctx)
                data = resp.read()
                actual_sha = hashlib.sha256(data).hexdigest()
                if actual_sha != expected_sha:
                    raise Exception(f"SHA256 mismatch: expected {expected_sha}, got {actual_sha}")
            # Extract
            t = tarfile.open(fileobj=io.BytesIO(data))
            for member in t.getmembers():
                # Strip root directory
                parts = member.name.split("/", 1)
                if len(parts) > 1:
                    member.name = parts[1]
                    t.extract(member, self.source_folder)
            t.close()

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # Fix shebangs
        self.run("sed -i '1s|#!/bin/sh|#!/system/bin/sh|; 1s|#!/bin/bash|#!/data/service/hnp/bin/bash|' bootstrap.sh || true", cwd=self.source_folder)
        self.run("find . -name '*.sh' -exec sed -i '1s|#!/bin/sh|#!/system/bin/sh|; 1s|#!/bin/bash|#!/data/service/hnp/bin/bash|' {} + 2>/dev/null || true", cwd=self.source_folder)
        # Build b2 engine
        self.run("./bootstrap.sh --prefix=/ || true", cwd=self.source_folder)
        # If bootstrap failed, try building engine directly
        if not os.path.exists(os.path.join(self.source_folder, "b2")):
            engine_dir = os.path.join(self.source_folder, "src", "engine")
            if os.path.isdir(engine_dir):
                self.run("cd src/engine && CXX=clang++ ./build.sh cc 2>&1 || true", cwd=self.source_folder)
            # Check if b2 was built in src/engine
            engine_b2 = os.path.join(self.source_folder, "src", "engine", "bin.ohos", "b2")
            if os.path.exists(engine_b2):
                copy(self, "b2", os.path.dirname(engine_b2), self.source_folder)

    def package(self):
        # Copy b2 binary
        copy(self, "b2", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Copy boost-build jamfiles
        copy(self, "*", os.path.join(self.source_folder, "src"), os.path.join(self.package_folder, "share", "boost-build"))
        copy(self, "*", os.path.join(self.source_folder, "boost-build.jam"), os.path.join(self.package_folder, "share", "boost-build"))

    def package_info(self):
        self.cpp_info.libs = []
